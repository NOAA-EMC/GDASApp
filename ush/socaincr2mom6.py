#!/usr/bin/env python3
import xarray as xr
import argparse
import os
import numpy as np
from netCDF4 import Dataset
import ufsda


def socaincr2mom6(incr, bkg, grid, incr_out, nsst_yaml=None):
    """
    Process the JEDI/SOCA increment file and create a MOM6 increment file
    with the correct variable names and dimensions.

    Parameters:
    incr (str): path to the JEDI/SOCA increment file
    bkg (str): path to the background file
    grid (str): path to the grid file
    incr_out (str): path to the output MOM6 increment file
    nsst_yaml (path to yaml file): yaml config for merging the soca and
                                   Tref increment.
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

    # Merge soca and nsst increment
    if nsst_yaml is not None:
        # compute Tref increment and interpolate on the tripolar grid

        # get the nsst increment and the number of layers used to propagate
        # the incr down the water column
        nsst_config = YAMLFile(path=nsst_yaml)
        ds_tref_incr = xr.open_dataset(nsst_config['tref increment'])
        nlayers = float(nsst_config['nlayers'])
        tref_incr = ds_tref_incr['dtref'].values[:]

        # get the soca temp increment
        soca_incr = ds_incr['Temp'].values[:]

        # Merge the 2 increments
        for layer in range(nlayers):
            coef = 1 - (float(layer)/nlayers)
            soca_incr[0,layer,:,:] = coef * tref_incr[:,:] + (coef - 1.0)*soca_incr[0,layer,:,:]
        ds_incr['Temp'].values[:] = soca_incr[:]

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
    parser.add_argument("--nsst_yaml", required=False, default=None, help="The yaml file containing the nsst config")
    args = parser.parse_args()

    socaincr2mom6(args.incr, args.bkg, args.grid, args.out, nsst_yaml=args.nsst_yaml)
