import numpy as np
import RestingConnectome.cyclic_analysis as ca
from tqdm import tqdm
from scipy.signal import filtfilt, bessel, cheby2, butter
import pudb

def _band_pass(low_cut, high_cut, fs, filter_name, order=5):
    """ Helper function to implement band-pass filtering using the chosen filter.
    
    Arguments:
        low_cut: The lower cutoff frequency. 
        high_cut: The higher cutoff freqynecy. 
        fs: The sampling frequency 
        filter_name: The filter to use. 
        order: What order filter to use. 

    Returns: The filter coefficients. 
    
    """
    nyq = 0.5 * fs
    low = low_cut / nyq
    high = high_cut / nyq
    
    # Get filter coefficients
    filter_list = {'bessel': bessel(order, [low, high], btype='band'),
                   'chebyshev': cheby2(order, 4, [low, high], btype='band'),
                   'butterworth': butter(order, [low, high], btype='band')}
    b, a = filter_list[filter_name]
    return b, a


def _low_pass(low_cut, high_cut, fs, filter_name, order=5):
    """ Helper function to implement low-pass filtering using the chosen filter. 
    
    Arguments:
        low_cut: Irrelevant. Only present for code compatibility. 
        high_cut: The higher cutoff frequency. 
        fs: The sampling frequency. 
        filter_name: Which filter to use. 
        order: What order filter to use. 

    Returns: The filter coefficients. 
    """
    nyq = 0.5 * fs
    high = high_cut / nyq
    
    # Get filter coefficients
    filter_list = {'bessel': bessel(order, high, btype='low'),
                   'chebyshev': cheby2(order, 4, high, btype='low'),
                   'butterworth': butter(order, high, btype='low')}
    b, a = filter_list[filter_name]
    return b, a

# Maintain a private dictionary of filters to use
_filters = {'band1': _band_pass(low_cut=0.008, high_cut=0.08, fs=1/0.72, filter_name='bessel'),
            'band2': _band_pass(low_cut=0.008, high_cut=0.5, fs=1/0.72, filter_name='bessel'),
            'low_pass': _low_pass(low_cut=0.00, high_cut=0.6, fs=1/0.72, filter_name='bessel'),
             None: lambda x: x}


class RHCPBase:
    """ The base class for the HCP data that handles the computational bits"""

    def __init__(self, shelf, norm='sqr', trend='linear', gsr=False, filter_type=None):
        """ At initialization one must specify which `shelf` object to use. 

        Arguments:
            norm: The normalization procedure to use (string, default 'sqr')
            trend: Then trend remove to use (string, default 'linear')
            gsr: Whether to perfrom global signal regressions (boolean, default False)
            filter_type: What kind of filtering to use on the time series (string/None, default None)
        """

        # Define properties as strings 
        self.norm = norm
        self.trend = trend
        self.filter = filter_type
        self.gsr = gsr

        # Define private counterparts of properties that are functions
        self._norm = ca.norms[norm][1]
        self._gsr = {True: ca.gs_regression, False: lambda x: x.T}
        self._filter = _filters[filter_type]

        # For convenience parse into more familiar terminology
        self._session_sort = {'REST1_LR': 'Session1', 'REST1_RL': 'Session1',
                              'REST2_LR': 'Session2', 'REST2_RL': 'Session2'}
        
        self._run_sort = {'REST1_LR': 'Run1', 'REST1_RL': 'Run2', 
                          'REST2_LR': 'Run1', 'REST2_RL': 'Run2'}

        # Start actual processing. 
        self.samples, roi_list = list(), list()
        for key, scans in tqdm(shelf.items()):
            for scan, data in scans.items():
                if scan != 'metadata':
                    time_series = self._gsr[gsr](np.asarray(list(data.values())).T)
                    normed_ts = self._norm(ca.detrend(ca.mean_center(time_series)))
#                    cyc_normed_ts = self._norm(ca.detrend(ca.mean_center(ca.match_ends(time_series))))

                    if filter_type:
                        normed_ts = filtfilt(*self._filter, time_series)

                    lret = ca.cyclic_analysis(normed_ts, p=1)
                    lm, lphases, lperm, sorted_lm, leigenvalues = lret  # Lead matrix
                    cvm = np.cov(normed_ts) * normed_ts.shape[1]        # Covariance matrix
                    crm = np.corrcoef(normed_ts)                        # Correlation matrix
                    
                    fhm = cvm + 1j*lm                                   # Fused Hermmitian matrix
                    fret = ca.sort_lead_matrix(fhm)
                    _, fphases, fperm, _, feigenvalues = fret

                    
                    # Check if all samples have same ROIS
                    temp_rois = list(data.keys())
                    if not roi_list:
                        roi_list.append(sorted(temp_rois))
                    elif sorted(temp_rois) != roi_list[0]:
                        roi_list.append(sorted(temp_rois))
                        raise Exception

                    self.samples.append({'Name': key, 'TimeSeries': normed_ts,'ULM':  lm, 
                                         'SLM': sorted_lm, 'CVM': cvm, 'LPhases': lphases, 'CRM': crm,
                                         'FHM': fhm, 'LPermutation': lperm, 'LEigenvalues': leigenvalues,
                                         'Session': self._session_sort[scan],'FPermutation': fperm, 
                                         'FEigenvalues': feigenvalues, 'FPhases': fphases,
                                         'Run': self._run_sort[scan], 'Metadata': scans['metadata']})

        self.rois = temp_rois
        self.removed_samples, self.deleted_samples = list(), list()
        self.removed_counter, self.data_counter = dict(), dict()
        self.sessions, self.runs = set(), set()
        self.covariance_matrix, self.projectors, self.cov_eigenvalues = None, None, None
        self.n_males, self.n_females, self.age_data = None, None, None
        self.__reset()

    def __dim__(self):
        return len(self.rois)

    def __len__(self):
        if not self.samples:
            return 0
        else:
            return len(self.samples)

    def __iter__(self):
        yield from self.samples

    def __str__(self):
        if not self.samples:
            return "Uninitialized RestingConnectome Data Object"
        else:
            header = "="*80
            title = "\t\tRestingConnectome data object\n"
            n_unique = len(set([sample['Name'] for sample in self]))
            string_uni = f"Number of unique subjects: {n_unique}"
            n_men = f"Number of men: {self.n_males}"
            n_women = f"Number of women: {self.n_females}"
            n_age1 = f"\nNumber of subjects in age group '22-25':\t{self.age_data['22-25']}"
            n_age2 = f"Number of subjects in age group '26-30':\t{self.age_data['26-30']}"
            n_age3 = f"Number of subjects in age group '31-35':\t{self.age_data['31-35']}"
            n_age4 = f"Number of subjects in age group ' >=36':\t{self.age_data['36+']}"
            n_bold = f"\nTotal number of BOLD time series: {len(self)}"
            footer = "="*80
    
            return "\n".join((header, title, string_uni, n_men, n_women, n_age1, n_age2, 
                              n_age3, n_age4, n_bold, footer))

    def __reset(self):
        """ Re-calculates covariance structure.

            The reset() method is useful after removing or adding data to the analysis 
            - often we remove outliers or subjects that showed too much motion.
        """
        if not self.samples:
            print('Error: Data has not been loaded yet!')
        else:
            self.sessions = set([sample['Session'] for sample in self.samples])
            self.runs = set([sample['Run'] for sample in self.samples])
            temp_var = [sample["ULM"][np.tril_indices_from(sample['ULM'],1)] for sample in  self]
            self.covariance_matrix = np.cov(np.asarray(temp_var).T)
            self.projectors, self.cov_eigenvalues, _ = np.linalg.svd(self.covariance_matrix)
            self.n_males = len(set([sample['Name'] for sample in self 
                                    if sample['Metadata'].loc['Gender']=='M']))
            self.n_females = len(set([sample['Name'] for sample in self 
                                      if sample['Metadata'].loc['Gender']=='F']))
            temp_var = set([sample["Metadata"].loc["Age"] for sample in self])
            self.age_data = {item: len(set([sample["Name"] for sample in self 
                                        if sample['Metadata'].loc["Age"]==item])) for item in temp_var}

    def remove_roi(self, roi):
        """ Function to remove a region of interest from the data set (from all samples). 
            Must call recompute.

            Arguments:
                roi: The roi to be removed specified as a string.

            Function is destructive, a roi removed from analysis cannot be added back in.  
            The instance's recompute method must be called manually.
        """

        if roi in self.rois:
            idx = self.rois.index(roi)
            for sample in self.samples:
                sample['TimeSeries'] = np.delete(sample['TimeSeries'], obj=idx, axis=0)
            self.rois.remove(roi)
        else:
            raise LookupError
    
    def mod_samples(self, op, idxs):
        """ Function to add or remove samples from analysis. 
        
            Arguments:
                op: The operation to perform, 'add' or 'rem' (remove). Type is string.
                idxs: The names of the subjects that you want to add or remove from analysis.
                    Type is a list of strings
        """
        if not type(idxs) == list:
            print('Error: mod_samples must be called with a list of sample names!')
        if op == 'rem':
            for idx in idxs:
                idx_list = [sample for sample in self.samples if sample['Name'] == idx]
                if idx_list != []:
                    for item in idx_list:
                        self.deleted_samples.append(item)
                        self.samples.remove(item)
                else:
                    raise KeyError
        elif op == 'add':
            for idx in idxs:
                idx_list = [sample for sample in self.deleted_samples if sample['Name'] == idx]
                if idx_list != []:
                    for item in idx_list:
                        self.samples.append(item)
                        self.deleted_samples.remove(item)
                else:
                    raise KeyError
        else:
            print("Argument `op` must be one of 'rem', 'add'")
            raise TypeError
        self.__reset()
        return self

    def edit_time_series(self, sub, run, session, edit_idx):
        """ Function to edit a specific time series entity. MUST CALL recompute manually.

            Arguments:
                sub: Name of subject to remove. String.
                run: Specific run of that subject to edit. String.
                session: The session the specified run belongs to. String.
                edit_idx: Numpy s_ objects corresponding to slices in the time series that one wishes to KEEP.

            All arguments are required to prevent accidental edits to time series data.
        """

        for sample in self.samples:
            if sample['Name'] == sub and sample['Run'] == run and sample['Session'] == session:
                if type(edit_idx) == slice:
                    sample['TimeSeries'] = sample['TimeSeries'][:, edit_idx]
                elif type(edit_idx) == tuple:
                    first = True
                    for idx in edit_idx:
                        if first:
                            temp = sample['TimeSeries'][:, idx]
                            first = False
                        else:
                            temp = np.concatenate((temp, sample['TimeSeries'][:, idx]), axis=1)
                    sample['TimeSeries'] = temp
                else:
                    print('Error: Given slicing is not comprehensible!')

    def __recompute(self):
        raise NotImplementedError


