# PyHCP

See [release notes](https://github.com/iabraham/pyhcp/releases).

## Introduction 

This is a repo to download [HCP](https://db.humanconnectome.org/) data using Python, subject by subject, pre-process it to extract timeseries data, and then delete the large image files in parallel all using Python and R. To use this repo you will need:

 * Anaconda and Python >= 3.6
 * An account with the HCP database
 * Amazon S3 access with the HCP database. We will use the `boto3` package for Amazon S3 access. See [here](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#configuration'') on configuring your credentials. 
 * [Workbench](https://www.humanconnectome.org/software/connectome-workbench) installed and the `wb_command` added to your PATH variable.

Exact instructions for doing the above have been purposely avoided because they are platform dependent. See below for a quick test to see whether you have succeeded. 

Currently the repo downloads dense time series (*dtseries*), dense labels (*dlabels*) and generates parcellated timeseries using Workbench (*ptseries*). Then it parses the CIFTI2 format parcellated timeseries to simply return a python dictionary whose keys are ROI names and values are time series data. 

Most of these instructions are for a Linux machine and have been tested out using Ubuntu 18.04 with Conda 4.6.7 and Python 3.7. 

## The environment 

To set up the Anaconda use the `environment.yml` file in the repo. The build numbers as well as version numbers have been excluded to let conda figure out what is best for the versioning on your platoform. 

	conda env create -f environment.yml

## The module
This is  a short explanation of the inner workings of the code in this repository. There are two main files, `download_hcp.py` and `automate.py`

 - `download_hcp` is best thought of as a module that implements sub functions for downloading, processing and cleaning up remainder files.
 - The three main functions are `download_subject(), process_subject()` and `clean_subject()`. 
 - The `download_subject()` function does what it says, it downloads data regarding a particular subject id like '100610'. _But_ it also filters the downloads for what _you_ need. Currenty the filtration keywords are hardcoded in `download_subject()`. You need to have AWS S3 access/credentials and `boto3` installed for this function to work. 
 - We implement `download_hcp.process_subject()` to run the workbench command. It should takes the dense time series (*.dtseries*) and a parcellation label file (*.dlabel*) as input. It returns a list of output files. To call workbench it uses the [`subprocess`](https://docs.python.org/3.7/library/subprocess.html) module. You need to have workbench downloaded, installed, and its binaries added to your path for this to work. 
 - We implement `download_hcp.clean_subject()` to clean up the large downloaded files once we have generated the parcellated time series. Its input is a list of files to keep on disk. It _should_ return nothing but utilizing [`map`](https://docs.python.org/3/library/functions.html#map) for parallelizing means functions _have_ to return something (see below).
 - We also display disk usage statistics during runtime.
 - `automate.py` calls above functions using python's parallelism enabling modules

#### Testing 1
If you have Amazon S3 and `boto` set up correctly with your credentials, you should be able to activate your environment, fire up python, and run 

	from download_hcp import *
	    dfiles = download_subject('100610')
	
and get no errors. 


#### Testing 2
If you have workbench installed and correctly added to path, then in your conda environment, you should be able to fire up python and say 

	import subprocess
	subprocess.run(['wb_command','-help'])
	

and get meaningful output. 

## Parallelizing 

Prof. YMB suggested that having large amounts of RAM even with just a few cores should allow for some parallelization: each of the `*_subject()` functions should be parallelizable using the [`multiprocessing`](https://docs.python.org/3.7/library/multiprocessing.html) package. This is easy a la [functional programming](https://en.wikipedia.org/wiki/Functional_programming)!

 - The `do_subject()` function chains together the above functions so that we can use `multiprocessing.Pool.map()` function on our list of subject ids. The last function in the chain should return the final python object to be stored on disk corresponding to each subject.
 - We implement a `process_ptseries()` function that can be called by `clean_subject()`. This function should take the generated _*ptseries*_ file and return a python dictionary containing ROI names and related time series. The `clean_subject()` function, that originally had nothing to return, can now return this object so that `map` works. (recall, `map` applies a function to each element of a list, and in particular can _never_ change the length of a list).

Note how `do_subject` really only does:
	
	clean_subject(idx, process_subject(*download_subject(idx)))

and parallelization only involves:

	with mp.Pool(N) as pool:
    	    result = pool.map(do_subject, subject_ids)
	

where `N` is the number of parallel processes. That's so clean even I am surprised that it worked out this way.


---

# Using rpy2 for CIFTI2

> **Note:** The installation of `R::cifti` below is no longer needed to be done manually since [v2](https://github.com/iabraham/pyhcp/releases/tag/v0.2). The module should automatically check if it exists, and if not, install it for you. 

We utilize an R module in this repo. If you set up the environment using the provided .yml file, and it worked without errors you should be good. Else you need to first, install rpy2 for conda using:

	conda install rpy2

on your environment in use. That should install the R packages needed to use R from within python. Next install the `cifti` package from CRAN:
	
	# import rpy2's package module
	import rpy2.robjects.packages as rpackages
	
	# import R's utility package
	utils = rpackages.importr('utils')
	utils.install_packages('cifti')

It should prompt you to pick a CRAN server for the session. If the installation is successful, it should end with

	.
	.
	** building package indices
	** installing vignettes
	** testing if installed package can be loaded
	* DONE (cifti)

You can confirm successful installation by opening python and running:
	
	from rpy2.robjects.packages import importr
	importr('cifti')
	
which should return:
 
	>>> importr('cifti')
	rpy2.robjects.packages.Package as a <module 'cifti'>

You may have to install a development packageis on your system for `xml2`, etc. Just use `sudo apt-get install xml2-dev` or whatever is missing. 

Alternatively, you can set up the environment using the `environment.yml` file.

# How to use pickled Py object

The code on successful run should place a file called `hcp_data.bin` in the `HCP_1200` folder. You can access the content of this file as follows:

    import gzip, pickle
    import numpy as np

    with gzip.open('hcp_data.bin') as s:
        data = pickle.load(s)

    print('Have subjects:')

    for key in data.keys():
        print('\t' + str(key))

    for key, scans in data.items():
        print('\nFor subject: ' + str(key) + '\thave:')
        for scan, data_dict in scans.items():
            if scan != 'metadata':
                print('Scan: \t', scan)
                print('With ROIs:\n', '\n'.join(list(data_dict.keys())))
            else:
                print('Subject age:\t', data_dict.loc['Age'])

