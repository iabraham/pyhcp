from RestingConnectome.RHCPBase import RHCPBase
import matplotlib.pyplot as mpl
import matplotlib
import pudb
import numpy as np
from numpy import random as nprandom
from mpl_toolkits.mplot3d import Axes3D
from sklearn.decomposition import PCA, TruncatedSVD, FactorAnalysis, KernelPCA


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


def _label_generator(sample):
    l1 = sample['Name']
    l2 = '-'.join((sample['Session'], sample['Run']))
    return "\n".join((l1,l2))


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

        if sub_samples is None:
            print('Error! No such time series found!')
            raise LookupError

        # Depending on arguments plot appropriately
        for sample in self._parse_plot_args(session, run, sub_samples):
            self._ts_plot_helper(sample, matrix=mat)

        mpl.show(block=block)
   
    def _parse_plot_args(self, session, run, samples):
        """ Helper function to parse arguments appropriately. """

        if samples is None:
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

        if sub_samples is None:
            print('Error! Subject not found')
        else:
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

    def phase_plot(self, fig, axis, sub, session, run):
        raise NotImplementedError

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
        """ Helper function that does the actual plotting. For feature matrices. 

            Arguments:
                sample: An element of self.samples
                matrix: A string specifying which matrix to visualize. Must be 'ULM', 'SLM' of 'CM'
        """
        import mpldatacursor

        mpl.figure()
        try:
            mpl.imshow(sample[matrix], interpolation=None)
        except KeyError:
            print('Error! Matrix not found. "mat" must be ULM, CM or SLM')
        mpl.title(matrix + '-' + sample['Name'] + ':' + sample['Session'] + '-' + sample['Run'])
        mpl.colorbar()
        mpldatacursor.datacursor(bbox=dict(alpha=1, fc='w'), formatter=self._label_point)


    def _ts_plot_helper(self, sample, matrix, rois=None):
        """ Helper function that does actually plotting. For time-series data. 
        
            Arguments:
                sample: One element of self.samples
                matrix: One of 'TimeSeries' or 'NormedTS'
                rois: An optional argument supplied as a lisst of which ROIS to 
                    plot in the visualization. 
        """

        import mpldatacursor 

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

        col = ['b', 'g', 'r', 'c', 'm', 'y', 'k']   # List of colors
        used = []                                   # List of used colors
        per_scatter_label = list()                  # We need a list of labels per call to scatter
        n = len(self.rois)

        for group in groups: # Currently this is gender, but can look at other options.
            by_group = [sample for sample in self if sample["Metadata"].loc["Gender"] == group]
            (label, data) = zip(*[(_label_generator(sample)+'\n' + group, 
                                  sample[mat][np.triu_indices(n, 1)]) for sample in by_group])
            xy = self._dim_reducer.fit_transform(np.asarray(data))
            c = nprandom.choice(col)
            while c in used:
                c = nprandom.choice(col)
            used.append(c)
            ax.scatter(xy[:, 0], xy[:, 1], c=c, label=group)
            per_scatter_label.append(label)

        return per_scatter_label


