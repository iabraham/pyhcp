from download_hcp import do_subject
import multiprocessing as mp 
from rpy2.robjects.packages import importr
import zipshelve
from pickle import HIGHEST_PROTOCOL
from datetime import datetime

batch_size = 4


def batches(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


def main():

    # Read in subject list as a list

    from rpy2.rinterface import RRuntimeError as RRE

    try:
        cifti = importr('cifti')
    except RRE:
        utils = importr('utils')
        utils.install_packages('cifti')

    with open('subjectlist.txt') as stream:
        subject_ids = stream.readlines()

    # Strip newline characters
    subject_ids = [idx.strip() for idx in subject_ids]
    fin = 'HCP_1200/hcp_data_'

    # Download and process. `procs` is # of processors
    procs = 4
    print(datetime.now())

    for i, batch in enumerate(batches(subject_ids, batch_size)):
        
        with mp.Pool(procs) as pool:
            result = zip(batch, pool.map(do_subject, batch))

        print('Shelving batch: \t', i)
        fname = fin + str(i) + '.gdb'

        with zipshelve.open(fname, protocol=HIGHEST_PROTOCOL) as shelf:
            for key, value in result:
                shelf[key] = value

    print(datetime.now())

    # # Serial instead of parallel?
    #
    # datum = dict()
    # for idx in subject_ids:
    #     datum[idx] = do_subject(idx)
    #
    # with zipshelve.open(fin, protocol=HIGHEST_PROTOCOL) as shelf:
    #     for key, value in datum:
    #         shelf[key] = value


if __name__ == "__main__":
    main()
