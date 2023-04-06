#!/usr/bin/env python3
import xarray as xr
import argparse
import os
import numpy as np
from netCDF4 import Dataset
import ufsda


def socaincr2mom6(incr, bkg, grid, incr_out):
    """
    Process the JEDI/SOCA increment file and create a MOM6 increment file
    with the correct variable names and dimensions.

    Parameters:
    incr (str): path to the JEDI/SOCA increment file
    bkg (str): path to the background file
    grid (str): path to the grid file
    incr_out (str): path to the output MOM6 increment file
    """

    # Make a copy of the incrememnt file
    # TODO: copying might not be necessary if we decide to not keep the
    #       original increment. TBD.
    ufsda.disk_utils.copyfile(incr, incr_out)

    # Open the input files as xarray datasets
    ds_incr = xr.open_dataset(incr_out)
    ds_bkg = xr.open_dataset(bkg)
    ds_grid = xr.open_dataset(grid)

    # Rename zaxis_1 to Layer in the increment file
    ds_incr = ds_incr.rename({'zaxis_1': 'Layer'})

    # Extract h from the background file and rename axes to be consistent
    ds_h = ds_bkg['h'].rename({'time': 'Time', 'zl': 'Layer', 'xh': 'xaxis_1', 'yh': 'yaxis_1'})

    # Replace h in the increment file with h from the background file
    ds_incr['h'][:] = ds_h.values[:]

    # Add tracer grid
    ds_incr['lon'] = ds_grid['lon']
    ds_incr['lat'] = ds_grid['lat']

    # Save increment
    ds_incr.to_netcdf(incr_out, mode='a')
    return


if __name__ == "__main__":
    epilog = ["Usage examples:",
              "   ./socaincr2mom6.py --bkg bkg.nc --incr incr.nc --grid grid.nc --out incrout.nc"]
    parser = argparse.ArgumentParser(description="Reformat a JEDI/SOCA increment to a format readable by MOM6 IAU.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=os.linesep.join(epilog))
    parser.add_argument("--bkg", required=True,
                        help="The background that contains the layer thicknesses valid for the increment")
    parser.add_argument("--incr", required=True, help="The JEDI/SOCA increment")
    parser.add_argument("--grid", required=True, help="The grid of the JEDI/SOCA increment")
    parser.add_argument("--out", required=True, help="The name of the output increment file")
    args = parser.parse_args()

    socaincr2mom6(args.incr, args.bkg, args.grid, args.out)
