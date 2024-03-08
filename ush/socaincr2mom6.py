#!/usr/bin/env python3
import xarray as xr
import argparse
import os
import numpy as np
from netCDF4 import Dataset
from scipy.interpolate import griddata
import ufsda
from wxflow import (FileHandler, YAMLFile)

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
    incr_in_out = []
    incr_in_out.append([incr, incr_out])
    FileHandler({'copy': incr_in_out}).sync()

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
        nsst_config = YAMLFile(path=nsst_yaml)
        sfc_fcst = nsst_config['sfc_fcst']
        sfc_ana = nsst_config['sfc_ana']
        tref_incr = trefincr2mom6(sfc_fcst, sfc_ana, grid)

        # get the number of layers used to propagate the incr down the water column
        nlayers = nsst_config['nlayers']

        # get the soca temp increment
        soca_incr = ds_incr['Temp'].values[:]

        # Merge the 2 increments
        I_filter = np.where(np.abs(np.squeeze(ds_grid['lat'].values[:])) > 60.0)
        tref_incr[I_filter] = 0.0
        for layer in range(nlayers):
            coef = 1 - (layer/nlayers)
            soca_incr[0, layer, :, :] = coef * tref_incr[:, :] + (coef - 1.0)*soca_incr[0, layer, :, :]

        ds_incr['Temp'].values[:] = soca_incr[:]

    # Save increment
    ds_incr.to_netcdf(incr_out, mode='a')
    return


def trefincr2mom6(bkgfile, anlfile, ocngridfile):
    """
    Create tref increment from FV3 and interpolate it to MOM6 grid.

    Parameters:
    bkgfile (str): path to FV3 background file with tref (prob. sfcf006)
    anlfile (str): path to FV3 analysis file with tref (prob. sfcanl)
    ocngridfile (str): path to the MOM6 grid file

    Returns:
    momtrefinc (2D array): FV3 tref increment on MOM6 grid
    """

    # compute increment
    ds_bkg = xr.open_dataset(bkgfile)
    ds_anl = xr.open_dataset(anlfile)
    incval = ds_anl['tref'].values-ds_bkg['tref'].values
    incval[ds_bkg['land'].values == 1] = 0.0

    # get ocean grid
    ocngrid = xr.open_dataset(ocngridfile)
    momlats = ocngrid['lat'].values.squeeze()
    momlons = ocngrid['lon'].values.squeeze()

    # get atmos gaussian grid and rotate to match the ocean grid
    fv3lats = ds_bkg['grid_yt'].values
    fv3lons = ds_bkg['grid_xt'].values
    momlon_max = np.max(momlons)
    fv3lons[fv3lons >= momlon_max] = fv3lons[fv3lons >= momlon_max] - 360
    fv3longrid, fv3latgrid = np.meshgrid(fv3lons, fv3lats)

    momtrefinc = griddata((fv3longrid.reshape(-1), fv3latgrid.reshape(-1)),
                          np.squeeze(incval).reshape(-1),
                          (momlons, momlats),
                          method='nearest')

    return momtrefinc


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
