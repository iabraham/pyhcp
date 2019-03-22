from download_hcp import do_subject
import multiprocessing as mp 
import gzip, pickle
from rpy2.robjects.packages import importr
import zipshelve
from pickle import HIGHEST_PROTOCOL

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

    # Download and process. `procs` is # of processors
    procs = 4
    
    with mp.Pool(procs) as pool:
        result = zip(subject_ids, pool.map(do_subject, subject_ids))
    
    print('Shelving returned data')
    fin = 'HCP_1200/hcp_data'

    with zipshelve.open(fin, protocol=HIGHEST_PROTOCOL) as shelf:
        for key, value in result:
            shelf[key] = value

    # Serial instead of parallel?

#    for idx in subject_ids:
#        datum = do_subject(idx)
#        breakpoint()


if __name__ == "__main__":
    main()
