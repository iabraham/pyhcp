The file metadata.csv contains publicly accessible metadata regarding the scans in the HCP S1200 release. In using this repository and the data contained in it you are agreeing to the Open Access Terms established by the Connectome Organization.

The file `automate.py` in the parent folder downloads HCP data in batches and places them in one [`gdb`](https://www.gnu.org.ua/software/gdbm/) file per batch. 

# How to use shelved Py object

The code on successful run should place three files called `hcp_data_X.gdb` in the `HCP_1200` folder where the `X`'s correspond to batch number. You can access the content of these files as follows:

```python
import zipshelve
from pathlib import Path
    
fin = Path('HCP_1200/hcp_data_N.gdb')	#Replace N with integer appropriately
	
with zipshelve.open(fin, mode='r') as shelf:
    print('Have subjects:')

# Can also call shelf.ls() instead of for loop
    for key in shelf.keys():
        print(key)

    for key, scans in shelf.items():
        print('\nFor subject: ' + str(key) + '\thave:')
        for scan, data_dict in scans.items():
            if scan != 'metadata':
	        print('Scan: \t', scan)
	        print('With ROIs:\n', '\n'.join(list(data_dict.keys())))
            else:
	        print('Subject age:\t', data_dict.loc['Age'])
```

The [`shelve`](https://docs.python.org/3/library/shelve.html) module wraps around pickling, by loading only the necessary key from disk (as opposed to `pickle.load()` which would load the whole data-set into memory). We move from `pickle` to `shelve` because pickling the whole data set will likely cause memory issues. The use of disk as opposed to RAM for hold data will cause some parallelization challenges, but that is to be worked out. 

**Note:** The files [`hcp_data.gdb`](https://uofi.box.com/s/lwbzqvrkswmwhjbmlxsh7o7gvi23sudc) (Illinois log-in required) and [`mini_hcp.gdb`](https://uofi.box.com/s/z25w1r25lc9swrna4dk3qccpky9tb6f7) (publicly available) mentioned in [`pyhcp/to_npz.py`](https://github.com/iabraham/pyhcp/blob/cyclicity/to_npz.py) can be downloaded.

# A `gdbm` issue

On Linux machines, if the `gdbm` module is not installed then `shelve` modules' readonly flag when opening does not work. This is an issue caused by the fact that Anaconda environment uses its own `lib-dynload` directory so even running

`sudo apt-get install python3-gdbm` 

may not fix the issue. To get around this (after running the above command) run:

`dpkg -L python3-gdbm`

and examine the output for a file with name of the form: `_gdbm.cpython-3Xm-x86_64-linux-gnu.so`. This is the dynamic library we need. Then with the Anaconda environment activated run:

`cd $(python -c 'import sys; [print(x) for x in sys.path if "lib-dynload" in x]')`

to `cd` into the Anaconda environment's `lib-dynload` folder. Next copy the above file dependeing on `36m` or `37m` into this folder. This should fix the issue. To confirm run:

```Python
import shelve

with shelve.open('test_shelf.gdb') as s:
    s['key1'] = {'int': 10,'float': 9.5, 'string': 'Sample data'}

with shelve.open('test_shelf.gdb', flag='r') as s:
    existing = s['key1']

with shelve.open('test_shelf.gdb', flag='r') as s:
    print('Existing:', s['key1'])
    s['key1'] = 'new value'

with shelve.open('test_shelf.gdb', flag='r') as s:
    print('Existing:', s['key1'])
```

on the Python prompt to confirm you get the error: `_gdbm.error: Reader can't store`.  If the problem is **not** fixed the output will be `Existing: new value` which means the readonly flag did **not work.**. 


