from download_hcp import do_subject
import multiprocessing as mp 
import gzip, pickle
from rpy2.robjects.packages import importr



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
    procs = 2
    
    with mp.Pool(procs) as pool:
        result = pool.map(do_subject, subject_ids)
    
    print('Pickling returned data')

    # `result` is a list of dictionaries, but has no subject
    # identifier so we make a new dictionary
    
    data = dict(zip(subject_ids, result))
    
    with gzip.open('HCP_1200/hcp_data.bin', 'wb') as stream:
        pickle.dump(data, stream)

    # Serial instead of parallel?

#    for idx in subject_ids:
#        datum = do_subject(idx)
#        breakpoint()


if __name__ == "__main__":
    main()
