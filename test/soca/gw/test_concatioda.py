import ufsda
import ufsda.soca_utils
import os
import sys


# Define a function that duplicates a file
def duplicate_obs(src_filename):
    if os.path.isfile(src_filename):
        base_filename = os.path.basename(src_filename)
        for nfile in list(range(2)):
            print(nfile)
            dest_filename = base_filename+'.'+str(nfile)
            print(f"{src_filename} ---> {dest_filename}")
            ufsda.disk_utils.copyfile(src_filename, dest_filename)
    else:
        raise Exception(f"{src_filename} does not exist")


# Get the directory where the files to be duplicated are located from command-line arguments
obsdir = sys.argv[1]

# Test the concatenation for these obs types
obslist = ['adt_j3_20180415.nc4', 'sst_noaa19_l3u_20180415.nc4']
for fname in obslist:
    iodafname = os.path.join(obsdir, fname)
    duplicate_obs(iodafname)
    iodafname = os.path.join(obsdir, '..', 'gw', 'concatioda', fname)
    ufsda.soca_utils.concatenate_ioda(iodafname)
