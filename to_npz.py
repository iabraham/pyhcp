import zipshelve
from pathlib import Path
import numpy as np
from RestingConnectome.RHCPCluster import RHCPCluster
import matplotlib.pyplot as plt
from scipy.spatial.distance import squareform
import pudb
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, matthews_corrcoef

file1 = Path('mini_hcp.gdb')
file2 = Path('hcp_data.gdb')
folder = Path('HCP_1200')

with zipshelve.open(folder/file1, mode='r') as shelf:
    data = RHCPCluster(shelf, dim_reduction='pca', gsr=False, norm='tv', filter_type=None)

def write_mats(sample):
    try:
        sname = 'NPZ/' + sample['Name']
        mats = ['CRM', 'ULM', 'CVM']
        sess_map = {'Session1': 's1', 'Session2':'s2'}
        run_map = {'Run1': 'r1', 'Run2': 'r2'}
        for mat in mats:
            iterable = (sname, sess_map[sample['Session']], run_map[sample['Run']])
            fname = '_'.join(iterable)
            np.savez_compressed(fname, CRM=sample['CRM'], ULM=sample['ULM'], CVM=sample['CVM'])
        return True
    except:
        return False
    

to_remove = ['200008', '186949', '303624', '973770', '200109', '101410', 
             '473952', '550439', '200210']
data.mod_samples('rem', to_remove)

print(data)

# for sample in data:
#     res = write_mats(sample)

