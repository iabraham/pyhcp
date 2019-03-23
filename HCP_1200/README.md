# How to use shelved Py object

The code on successful run should place three files called `hcp_data.dat`, `hcp_data.bak` and `hcp_data.dir` in the `HCP_1200` folder. You can access the content of these files as follows:

```python
    import zipshelve
    from pathlib import Path
	
    fin = Path('HCP_1200/hcp_data')
	
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
