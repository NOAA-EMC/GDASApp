#!/usr/bin/env python3
# translate FV3-JEDI increment to FV3 readable format with delp and hydrostatic delz calculation
import argparse
import netCDF4 as nc
import numpy as np
import logging
import os


def jedi_inc_to_fv3(FV3ges, FV3JEDIinc, FV3inc):
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
    # Check if required input netcdf files exist.  If not present, exit with error message.
    try:
        with nc.Dataset(FV3ges, 'r'), nc.Dataset(FV3JEDIinc, 'r'):
            ncges = nc.Dataset(FV3ges, 'r')
            ncin = nc.Dataset(FV3JEDIinc, 'r')
            ncout = nc.Dataset(FV3inc, 'w', format='NETCDF4')
            create_fv3inc(ncges, ncin, ncout)

    except FileNotFoundError as e:
        logging.error(f"Error occurred with message {e}")
        raise


def create_fv3inc(ncges, ncin, ncout):

    # Copy over dimensions
    for name, dimension in ncin.dimensions.items():
        ncout.createDimension(name,
                              (len(dimension) if not dimension.isunlimited() else None))
    # Some global attributes
    ncout.source = 'jediinc2fv3_cube.py'
    ncout.comment = 'Increment produced by FV3-JEDI and modified for use by FV3 read'

    # Create all the dummy vertical coordinate variables
    nlevs = len(ncin.dimensions['pfull'])
    nx = len(ncin.dimensions['grid_xt'])
    ny = len(ncin.dimensions['grid_yt'])

    # Rename and change dimensionality of fields
    for name, variable in ncin.variables.items():
        dimsout = variable.dimensions[:]
        if len(variable.dimensions) == 5:
            dimsout_inc = dimsout

        if name == 'time_iso':
            x = ncout.createVariable(name, 'S1', dimsout)
        else:
            x = ncout.createVariable(name, 'f4', dimsout)

        ncout[name][:] = ncin[name][:]

    # Populate increment and guess fields
    #   Note:  increment and guess fields have same shape
    #     ps_inc is (time, lat, lon), ps_ges is {time, grid_yt, grid_xt)
    #     t_inc is (time, lev, lat, lon), t_ges is (time, pfull, grid_yt, grid_xt)

    ps_ges = ncges.variables['pressfc'][:]
    t_ges = ncges.variables['tmp'][:]
    q_ges = ncges.variables['spfh'][:]

    ps_inc = ncin.variables['pressfc'][:]
    t_inc = ncin.variables['tmp'][:]
    q_inc = ncin.variables['spfh'][:]

    # Compute analysis ps
    ps_anl = ps_ges + ps_inc

    # Set constants and compute derived constants
    grav = 9.80665
    airmw = 28.965
    h2omw = 18.015
    runiv = 8314.47
    rdry = runiv/airmw
    rvap = runiv/h2omw
    cpdry = 3.5*rdry
    fv = (rvap/rdry)-1
    rdog = rdry/grav
    kappa = rdry/cpdry
    kap1 = kappa+1.0
    kapr = 1.0/kappa

    # Get ak,bk from guess file
    nc_attrs = ncges.ncattrs()
    ak = ncges.getncattr('ak')
    bk = ncges.getncattr('bk')

    # Compute guess and analysis interface pressures
    prsi_ges = np.empty((1, 6, nlevs+1, ny, nx), float)
    prsi_anl = np.empty((1, 6, nlevs+1, ny, nx), float)
    for k in range(0, nlevs+1):
        prsi_ges[:, :, k, :, :] = ak[k] + bk[k]*ps_ges[:, :, :, :]
        prsi_anl[:, :, k, :, :] = ak[k] + bk[k]*ps_anl[:, :, :, :]

    # Compute pressure increment (delp_inc).  Compute
    # guess and analysis layer pressures using Philips method
    delp_inc = np.empty((1, 6, nlevs, ny, nx), float)
    prsl_ges = np.zeros((1, 6, nlevs, ny, nx), float)
    prsl_anl = np.zeros((1, 6, nlevs, ny, nx), float)
    for k in range(0, nlevs):
        dbk = bk[k+1] - bk[k]
        delp_inc[:, :, k, :, :] = ps_inc[:, :, :, :] * dbk
        prsl_ges[:, :, k, :, :] = ((prsi_ges[:, :, k+1, :, :]**kap1 - prsi_ges[:, :, k, :, :]**kap1) / (kap1*(prsi_ges[:, :, k+1, :, :] - prsi_ges[:, :, k, :, :])))**kapr
        prsl_anl[:, :, k, :, :] = ((prsi_anl[:, :, k+1, :, :]**kap1 - prsi_anl[:, :, k, :, :]**kap1) / (kap1*(prsi_anl[:, :, k+1, :, :] - prsi_anl[:, :, k, :, :])))**kapr

    # Write delp increment to output file
    x = ncout.createVariable('delp', 'f4', dimsout)
    ncout['delp'][:] = delp_inc[:]

    # Compute analysis temperature andl specific humidity
    t_anl = t_ges + t_inc
    q_anl = q_ges + q_inc

    # Compute guess and analysis virtual temperature
    tv_ges = t_ges * ( 1. + fv*q_ges )
    tv_anl = t_anl * ( 1. + fv*q_anl )

    # Compute guess and analysis delz and delz increment
    delz_ges = np.zeros((1, 6, nlevs, ny, nx), float)
    delz_anl = np.zeros((1, 6, nlevs, ny, nx), float)
    delz_inc = np.zeros((1, 6, nlevs, ny, nx), float)
    for k in range(0, nlevs):
        if k == 0:
            delz_ges[:, :, k, :, :] = rdog * tv_ges[:, :, k, :, :] * np.log(prsl_ges[:, :, k, :, :]/prsi_ges[:, :, k+1, :, :])
            delz_anl[:, :, k, :, :] = rdog * tv_anl[:, :, k, :, :] * np.log(prsl_anl[:, :, k, :, :]/prsi_anl[:, :, k+1, :, :])
        else:
            delz_ges[:, :, k, :, :] = rdog * tv_ges[:, :, k, :, :] * np.log(prsi_ges[:, :, k, :, :]/prsi_ges[:, :, k+1, :, :])
            delz_anl[:, :, k, :, :] = rdog * tv_anl[:, :, k, :, :] * np.log(prsi_anl[:, :, k, :, :]/prsi_anl[:, :, k+1, :, :])

        delz_inc[:, :, k, :, :] = delz_anl[:, :, k, :, :] - delz_ges[:, :, k, :, :]

    # Write delz increment to output file
    x = ncout.createVariable('delz', 'f4', dimsout)
    ncout['delz'][:] = delz_inc[:]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('FV3background', type=str, help='Input FV3 background file')
    parser.add_argument('FV3JEDIincrement', type=str, help='Input FV3-JEDI LatLon Increment File')
    parser.add_argument('FV3increment', type=str, help='Output FV3 Increment File')
    args = parser.parse_args()
    jedi_inc_to_fv3(args.FV3background, args.FV3JEDIincrement, args.FV3increment)
