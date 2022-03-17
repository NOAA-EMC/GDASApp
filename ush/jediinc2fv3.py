#!/usr/bin/env python3
# translate FV3-JEDI increment to FV3 readable format
import argparse
import netCDF4 as nc
import numpy as np
import os

vardict = {
    'ua': 'u_inc',
    'va': 'v_inc',
    'delp': 'delp_inc',
    'DELP': 'delp_inc',
    'delz': 'delz_inc',
    'T': 'T_inc',
    'sphum': 'sphum_inc',
    'liq_wat': 'liq_wat_inc',
    'o3mr': 'o3mr_inc',
    'ice_wat': 'icmr_inc',
    'lat': 'lat',
    'lon': 'lon',
}


def jedi_inc_to_fv3(FV3JEDIinc, FV3inc):
    assert os.path.exists(FV3JEDIinc), f"File {FV3JEDIinc} not found."
    assert os.path.exists(FV3JEDIinc), f"File {FV3JEDIinc} not found."
    # open netCDF files
    with nc.Dataset(FV3JEDIinc) as ncin, nc.Dataset(FV3inc, "w", format="NETCDF4") as ncout:
        # copy over dimensions
        for name, dimension in ncin.dimensions.items():
            if name == 'time':
                continue
            elif name == 'edge':
                nameout = 'ilev'
            else:
                nameout = name
            ncout.createDimension(nameout,
                                  (len(dimension) if not dimension.isunlimited() else None))
        # some global attributes
        ncout.source = 'jediinc2fv3.py'
        ncout.comment = 'Increment produced by FV3-JEDI and modified for use by FV3 read'
        # create all the dummy vertical coordinate variables
        nlevs = len(ncin.dimensions['lev'])
        pfull = range(1, nlevs+1)
        phalf = range(1, nlevs+2)
        levvar = ncout.createVariable('lev', 'f4', ('lev'))
        levvar[:] = pfull
        pfullvar = ncout.createVariable('pfull', 'f4', ('lev'))
        pfullvar[:] = pfull
        ilevvar = ncout.createVariable('ilev', 'f4', ('ilev'))
        ilevvar[:] = phalf
        hyaivar = ncout.createVariable('hyai', 'f4', ('ilev'))
        hyaivar[:] = phalf
        hybivar = ncout.createVariable('hybi', 'f4', ('ilev'))
        hybivar[:] = phalf
        # rename and change dimensionality of fields
        for name, variable in ncin.variables.items():
            if len(variable.dimensions) == 4:
                dimsout = variable.dimensions[1:]
            else:
                dimsout = variable.dimensions
            if name in vardict:
                x = ncout.createVariable(vardict[name], 'f4', dimsout)
                if len(variable.dimensions) == 4:
                    ncout[vardict[name]][:] = ncin[name][0, ...]
                else:
                    ncout[vardict[name]][:] = ncin[name][:]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('FV3JEDIincrement', type=str, help='Input FV3-JEDI LatLon Increment File')
    parser.add_argument('FV3increment', type=str, help='Output FV3 Increment File')
    args = parser.parse_args()
    jedi_inc_to_fv3(args.FV3JEDIincrement, args.FV3increment)
