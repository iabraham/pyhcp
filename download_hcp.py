import boto3, botocore
import os, subprocess
from pathlib import Path
from rpy2.robjects.packages import importr
import numpy as np 


def download_subject(sname):
    """ Given a subject ID will download resting state data from HCP AWS server

    Arguments:
        sname - the subject id

    Returns:
        A tuple consisting of list of dense time series and labels
    """

    s3 = boto3.resource('s3')

    #  Declare bucket name
    BUCKET_NAME = 'hcp-openaccess'
    bucket = s3.Bucket(BUCKET_NAME)

    # Append all keys( file names with full path) to a list
    key_list = [str(key.key) for key in bucket.objects.filter(Prefix='HCP_1200/' + sname)]

    print('-'*10, ' Downloading data for ...', sname)

    keyword1='Atlas_MSMAll_hp2000_clean.dtseries.nii'
    keyword2='aparc.32k_fs_LR.dlabel.nii'
    filtered_list1 = list(filter(lambda x: (keyword1 in x ), key_list))
    filtered_list2 = list(filter(lambda x: (keyword2 in x ), key_list))
    filtered_list = filtered_list1 + filtered_list2

    # Loop through keys and use download_file to download each key (file) to the directory where this code is running.
    for key in filtered_list: 
        try:
    	# Respect the directory structure
            os.makedirs(os.path.dirname(key), exist_ok=True)
            if not Path(key).is_file():
                s3.Bucket(BUCKET_NAME).download_file(key, key)
            else:
                print('Skipping download: ', key, '\tFile Exists!')
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
            else:
                raise KeyError

   #return dense_time_series, parcellation_labels, subject name
    return filtered_list1, filtered_list2, sname


def process_subject(dtseries, dlabels, sid):
    """ Runs the workbench parcellate command given a subjects dense time series files and parcellation label files.

    Arguments:
        dtseries - a list of dense time series
        dlabels - a list of parcellation labels
        sid - subject identifier for printing/diagnostics

    Returns:
        a list containing the workbench generated files

    """

    print('-'*10, ' Workbench processing ... ', sid)
    base_bash_command = "wb_command -cifti-parcellate"
    file_list = []

    for label in dlabels:
        for series in dtseries:
            # output file
            opfile = series.split('dtseries')[0] + 'ptseries.nii' # Include dlabel info later
            
            # Join together the components of the terminal command
            bash_command = " ".join([base_bash_command, series, label, "COLUMN", opfile])

            if not Path(opfile).is_file():
                # Run bash command using subprocess
                subprocess.run(bash_command.split())
            else:
                print('Skipping parcellation: ', opfile, '\tFile Exists!')

            file_list.append(Path(opfile))
    
    file_list.extend(list((map(Path, dlabels)))) 

    return file_list


def du(path):
    """Disk usage in human readable format (e.g. '2,1GB')"""
    import platform

    beginning = '"{0:N2} MB" -f ((Get-ChildItem' 
    end = '-Recurse | Measure-Object -Property Length -Sum -ErrorAction Stop).Sum / 1MB)'
    win_string = ' '.join([beginning, path, end])

    if platform.system() in ['Linux', 'Darwin']:
        return subprocess.check_output(['du','-sh', path]).split()[0].decode('utf-8')
    else:
        return subprocess.check_output(['powershell', win_string])



def process_ptseries(ptseries):
    """ Process the XML format ptseries to extract the ROI/time series file.

    Arguments:
        ptseries - The parcellated timeseries file.

    Returns:
        data_dict - A dictionary with keys as ROI names and values as timeseries
     """
    # Import the R module
    cifti = importr('cifti')

    # Read the data, datum is an R object
    datum = cifti.readCIFTI(ptseries)

    # Extract the cifti data into a python dictionary
    cifti_dict = {key: datum.rx2(key) for key in datum.names}
    
    # The key called 'Parcel' has data regarding ROI and voxel
    roi_names = list(cifti_dict['Parcel'].names)

    # The key called 'data' has a 'R' object matrix 
    # We create a dictionary with roi_names as keys and rows 
    # of data matrix as values and return it 

    return ptseries, dict(zip(roi_names, np.asarray(cifti_dict['data']))) 


def clean_subject(subject_id, keep_files):
    """ Cleans up data relating to a subject by removing all the files that are not given as argument.

    Arguments:
        subject_id - The id of the subject from HCP1200
        keep_files - A list of files to be kept, everything else will be removed.

    Returns:
        A python dictionary corresponding to the ROI/timeseries data
    """

    print('-'*10, ' Removing files for  ... ', subject_id, ' \n')

    del_files = list()
    spath = os.path.join('HCP_1200', subject_id)

    print('Size before:\t', du(spath))

    # Walk path and generate list of files to delete
    for root, folders, files in os.walk(spath):
        if not folders:
            for file_name in files:
                test_file  = os.path.join(root,file_name)
                if Path(test_file) in keep_files:
                    pass
                else:
                    del_files.append(test_file)

    
    # Now delete them and check if there are errors
    for file_name in del_files:
        try:
            os.remove(file_name)
        except OSError:
            print("Tried to remove a directory. This shouldn't be happening!")
            return False
 
    print('Size after:\t', du(spath))

    # Call the process_ptseries() function to generate python object from the 
    # CIFTI file
    pts = [str(f) for f in keep_files if 'ptseries' in str(f)]
    
    return list(map(process_ptseries, pts))


def do_subject(idx):
    """ The power of functional programming. Chain together multiple functions to create a new function
        that can be implemented in parallel.

       Arguments:
            idx - The id of the subject to process.
    """

    print("="*30, " Doing subject:\t ", idx, "="*30)
    return clean_subject(idx, process_subject(*download_subject(idx)))

