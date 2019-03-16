from download_hcp import do_subject
import multiprocessing as mp 
import gzip, pickle

with open('subjectlist.txt') as stream:
    subject_ids = stream.readlines()

subject_ids = [idx.strip() for idx in subject_ids]

with mp.Pool(2) as pool:
    result = pool.map(do_subject, subject_ids)

print('Pickling returned data')

data = dict(zip(subject_ids, result))

with gzip.open('HCP_1200/hcp_data.bin', 'wb') as stream:
    pickle.dump(data, stream)

# for idx in subject_ids:
#     do_subject(idx)
