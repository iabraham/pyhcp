from RestingConnectome.RHCPBase import RHCPBase
import matplotlib.pyplot as mpl
import matplotlib
import pudb
import numpy as np
from numpy import random as nprandom
from mpl_toolkits.mplot3d import Axes3D
from sklearn.decomposition import PCA, TruncatedSVD, FactorAnalysis, KernelPCA
import mpldatacursor
from copy import deepcopy

# Generally people want to look at a 2D visualization of the data set and they normally
# use something like PCA for it. Here we provide some dimensionality reduction mehtods
# for this purpose. 

reduction_methods = {'pca': PCA(), 
                     'kpca': KernelPCA(kernel='rbf'),
                     'factor': FactorAnalysis(),
                     'trunc_svd': TruncatedSVD(n_components=2278, n_iter=100)}


def _plotted_artists(ax):
    """ Return all the matplotlib artist objects associated with given axis object."""
    
    artists = (ax.lines + ax.patches + ax.collections + ax.images + ax.containers)
    return artists


def _formatter(**kwargs):
    """Helper function for mpldatacursor package."""

    return kwargs['point_label'].pop()


def _label_generator(sample, group):
    """ Helper function to generate labels for scatter plot. """
    l1 = sample['Name']
    l2 = '-'.join((sample['Session'], sample['Run']))
    return "\n".join((l1, l2, group))


def _plot_evec(fig, ax, sample, threshold_function, phase):
    """ Helper function to plot elements of eigenvector around complex plane. """

    if phase == 'FPhases':
        perm = 'FPermutation'
    else:
        perm = 'LPermutation'

    v = sample[phase][sample[perm]]
    title = sample['Name'] + ' in ' + sample['Session'] + '-' + sample['Run'] 
    fname = 'figures/' + sample['Name'] + '_' + sample['Session'] + '_' + sample['Run']
    lim = max(np.abs(np.amax(v)), np.abs(np.amin(v)))
    circ = mpl.Circle((0, 0), lim, color='k', fill=False)
    x = np.real(v).flatten()
    y = np.imag(v).flatten()
    ax.plot(x, y, 'ko:')
    ax.plot(x[0], y[0], 'ro')
    ax.add_artist(circ)
    ax.grid()
    mpl.title(title)
    mpl.xlim(right=1.1 * lim, left=-1.1 * lim)
    mpl.ylim(top=1.1 * lim, bottom=-1.1 * lim)
    lim = threshold_function(v)
    circ = mpl.Circle((0, 0), lim, color='b', fill=False, linestyle='dotted')
    ax.add_artist(circ)

    return list(sample[perm]), x, y


class RHCPCluster(RHCPBase):
    """ A subclass of RHCPBase that handles the visualization options """

    def __init__(self, shelf, **kwargs):
        """ Initialization call by pointing to appropriate `shelf` object. 
        
        Arguments:
            shelf: The .gdb file to use to initialize the data
            kwargs: The arguments required for the base class except the
                dimension reduction method for 2D scatter plot function that
                is strictly speaking an attribute of the subclass. """


        dim_reduction = kwargs.pop('dim_reduction')
        super().__init__(shelf, **kwargs)
        self._dim_reducer = reduction_methods[dim_reduction]
        self.mat_names = {'CRM': 'Correlation Matrix', 'ULM': 'Lead Matrix', 'FHM': 'Fused Hermitian Matrix'}

    def show_time_series(self, sub, run=None, session=None, rois=None, mat='TimeSeries', block=True):
        """ Function to display the time series data.

            Arguments:
                sub: The name of the subject whose time series data should be displayed.
                run: Which run the plot should correspond to (optional)
                session: Which session the plot should correspond to (optional)
                rois: Which ROIs to plot, by name (optional)

            If run and session are not specified, plots it for all matches of subject name.
        """

        # Get all samples with name match
        sub_samples = [sample for sample in self if sample['Name'] == sub]

        # Depending on arguments plot appropriately
        for sample in self._parse_plot_args(session, run, sub_samples):
            self._ts_plot_helper(sample, matrix=mat)

        mpl.show(block=block)
   
    def _parse_plot_args(self, session, run, samples):
        """ Helper function to parse session and run arguments in plot functions appropriately. """

        if samples is None:
            print('Error! No such combination found !')
            raise LookupError
        elif session is None:
            return iter(samples)
        elif session is not None and run is None:
            return iter([sample for sample in samples if sample['Session']==session])
        elif session is not None and run is not None:
            return iter([sample for sample in samples if 
                         sample['Session']==session and sample['Run']==run])
        else:
            raise AssertionError

    def show_mat(self, sub, mat='ULM', session=None, run=None, block=True):
        """ A function to visualize the matrices associated with samples.

            Arguments:
                sub: The subject identifier as a string
                mat: The matrix to display. A string which must be one of 'ULM', 'CM' and 'SLM'.
                session: Session identifier for the matrix of interest (optional)
                run: Run in the session specified (optional).

            If keyword arguments are not specified function displays the unsorted lead matrix 
            for all instances of the subject that it found.
        """

        matplotlib.rcParams.update({'font.size': 16})

        # Get all name matches
        sub_samples = [sample for sample in self if sample['Name'] == sub]

        # Depending on arguments plot appropriately
        for sample in self._parse_plot_args(session, run, sub_samples):
            self._mat_plot_helper(sample, matrix=mat)

        mpl.show(block=block)
        matplotlib.rcdefaults()

    def scatter(self, fig, ax, mat='ULM'):
        """ Function to make a 2D scatter plot of data by 'group' using dimension reduction method.

            Keyword arguments:
                fig: Specifies a figure object for call to matplotlib module
                ax: Specifies an exis object to use. 
                mat: Which matrix to flatten and use as start for 2D scatter plot

            `group` is tentatively gender. 
        """
        import mpldatacursor
        per_scatter_label = self._plot_by_group(ax, mat, ["M", "F"])

        axes = [ax for ax in fig.axes]
        scatters = [artist for ax in axes for artist in _plotted_artists(ax)]
 
        point_labels = dict(zip(scatters, per_scatter_label))
        mpldatacursor.datacursor(formatter=_formatter, 
                                 point_labels=point_labels, display='multiple')
        ax.legend()
 
        ax.grid(True)
        mpl.xlabel('Principal direction 1')
        mpl.ylabel('Principal direction 2')
        mpl.title('Scatter plot')

    def plot_rank(self, sub, session=None, run=None, mat='ULM'):
        """Function to make stem plots of the absolute value of the eigenvalues of the given mat """

        # Get all name matches
        sub_samples = [sample for sample in self if sample['Name'] == sub]

        # Depending on arguments plot appropriately
        for item in self._parse_plot_args(session, run, sub_samples):
            mpl.figure()
            eigs, _ = np.linalg.eig(item[mat])
            mpl.stem(np.abs(eigs))
            mpl.title(self.mat_names[mat] + item['Name'] + ':' + item['Session'] + '-' + item['Run'])

    def phase_plot(self, sub, phase='LPhases', session=None, run=None, threshold='rms'):

        threshold_function = {'rms':  lambda x : np.sqrt(np.mean(np.square(np.abs(x)))),
                              'mean': lambda x :np.mean(np.abs(x))}
        sub_samples = [sample for sample in self if sample['Name']==sub]

        for sample in self._parse_plot_args(session, run , sub_samples):
            fig = mpl.figure()
            ax = fig.add_subplot(111)
            perm, x, y = _plot_evec(fig, ax, sample, threshold_function[threshold], phase=phase)
            self._phase_labels(fig, ax, perm, x, y)

    def _label_point(self, **kwargs):
        """ A helper function for `mpldatacursor`. Generates a string to display when a scatter
        plot point is clicked. 
        """
        if kwargs is not None:
            try:
                return 'row = ' + self.rois[kwargs['i']] + '\ncol = ' + self.rois[kwargs['j']]
            except KeyError:
                pass

    def _mat_plot_helper(self, sample, matrix):
        """ Helper function that does the actual plotting for feature matrices. 

            Arguments:
                sample: An element of self.samples
                matrix: A string specifying which matrix to visualize. Must be 'ULM', 'SLM' of 'CM'
        """
        import mpldatacursor

        mpl.figure()
        try:
            mpl.imshow(sample[matrix], interpolation=None)
        except KeyError:
            print('Error! Matrix not found.')
        mpl.title(matrix + '-' + sample['Name'] + ':' + sample['Session'] + '-' + sample['Run'])
        mpl.colorbar()
        mpldatacursor.datacursor(bbox=dict(alpha=1, fc='w'), formatter=self._label_point)


    def _ts_plot_helper(self, sample, matrix, rois=None):
        """ Helper function that does actual plotting for time-series data. 
        
            Arguments:
                sample: One element of self.samples
                matrix: One of 'TimeSeries' or 'NormedTS'
                rois: An optional argument supplied as a lisst of which ROIS to 
                    plot in the visualization. 
        """

        if not rois:
            mpl.figure()
            for index, row in enumerate(sample[matrix].tolist()):
                mpl.plot(row, label=self.rois[index])
        else:
            mpl.figure()
            for roi in rois:
                try:
                    idx = self.rois.index(roi)
                    mpl.plot(sample[mat][idx, :].tolist(), label=roi)
                except ValueError:
                    print('Error! ROI ' + roi + ' not found!')
                    raise KeyError

        mpl.title(sample['Name'] + '-' + sample['Session'] + '-' + sample['Run'])
        mpl.xlabel('Time')
        mpldatacursor.datacursor(formatter='{label}'.format)


    def _plot_by_group(self, ax, mat, groups):
        """ Helper function to create a seperate/overlayed scatter plot for each group. 
            Funciotn should be called by the scatter function. 
        
        Argument:
            ax - A matplotlib Axis object to use 
            mat - The kind of matrix to be used
            groups - What groups are there in the analysis?
        """

        col = ['b', 'g', 'r', 'c', 'm', 'y', 'k']   # List of colors
        used = []                                   # List of used colors
        per_scatter_label = list()                  # We need a list of labels per call to scatter
        n = len(self.rois)

        for group in groups: # Currently this is gender, but can look at other options.
            by_group = [sample for sample in self if sample["Metadata"].loc["Gender"] == group]

            (label, data) = zip(*[(_label_generator(sample, group), 
                                  sample[mat][np.triu_indices_from(sample[mat], 1)]) 
                                  for sample in by_group])
            xy = self._dim_reducer.fit_transform(np.asarray(data))
            c = nprandom.choice(col)
            while c in used:
                c = nprandom.choice(col)
            used.append(c)
            ax.scatter(xy[:, 0], xy[:, 1], c=c, label=group)
            per_scatter_label.append(label)

        return per_scatter_label


    def _phase_labels(self, fig, ax, perm, x, y):
        """ Helper function to make the label elements in a phase plot. """
    
        label= list()
        for item in perm:
            label.append(self.rois[item])
        print_label = deepcopy(label)
        to_disp = '\n'.join(print_label)
        axes = [ax for ax in fig.axes]
        scatters = [artist for ax in axes for artist in _plotted_artists(ax)]
        pointlabel = {scatters[0]:label}
#        mpl.subplots_adjust(left=0.25)
#        mpl.gcf().text(0.02, 0.15, to_disp)
        num_label = [str(i) for i in range(1,69)]
        for label,x,y in zip(num_label,x,y):
            mpl.text(x+0.005,y+0.005,label)
        # mpl.show(block=False)
        # mpl.savefig(fname)
        mpldatacursor.datacursor(formatter=_formatter, point_labels=pointlabel, display='multiple')



