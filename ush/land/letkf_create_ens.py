import os
import numpy as np
from netCDF4 import Dataset
import sys
# Can silence the DeprecationWarning by add the following:
# from warnings import filterwarnings
# filterwarnings(action='ignore', category=DeprecationWarning, message='`np.bool` is a deprecated alias')
# routine to create pseudo-ensemble for use in LETKF-OI for snow depth
# reads in sfc_data restarts, and sets snowdepth to +/-
# perturbation, given stdev(ensemble) of B
# Clara Draper, October, 2021.

if (len(sys.argv) != 4):
    print('argument error, usage: letkf_create file_stub back_error')

fstub = sys.argv[1]
b = float(sys.argv[2])
workdir = sys.argv[3]

# 2 ens members
offset = b/np.sqrt(2)

print(f"adjusting {fstub}* by {str(offset)}")

sign = [1, -1]
ens_dirs = ['mem001', 'mem002']

for (mem, value) in zip(ens_dirs, sign):
    for tt in range(1,7):
        # open file
        out_netcdf = os.path.join(workdir, mem, f"{fstub}.sfc_data.tile{tt}.nc")
        # print (f"{out_netcdf}")
        with Dataset(out_netcdf, "r+") as ncOut:
            var_array = ncOut.variables["snwdph"][:]
            var_array = var_array + value*offset
            ncOut.variables["snwdph"][0, :, :] = var_array[:]
