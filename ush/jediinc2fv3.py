#!/usr/bin/env python3
# translate FV3-JEDI increment to FV3 readable format with delp and hydrostatic delz calculation
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
    't': 'T_inc',
    'T': 'T_inc',
    'sphum': 'sphum_inc',
    'liq_wat': 'liq_wat_inc',
    'o3mr': 'o3mr_inc',
    'ice_wat': 'icmr_inc',
    'lat': 'lat',
    'lon': 'lon',
}


def jedi_inc_to_fv3(FV3ges, FV3JEDIinc, FV3inc):
    # open netCDF files
    try:
        with nc.Dataset(FV3ges, 'r') as ncges, nc.Dataset(FV3JEDIinc,'r') as ncin, nc.Dataset(FV3inc, "w", format="NETCDF4") as ncout:
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
            nlats = len(ncin.dimensions['lat'])
            nlons = len(ncin.dimensions['lon'])

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
                    dimsout4 = dimsout
                elif len(variable.dimensions) == 3:
                    dimsout = variable.dimensions[1:]
                    dimsout3 = dimsout
                else:
                    dimsout = variable.dimensions

                if name in vardict:
                    if name == 'delp':
                        continue
                    if name == 'delz':
                        continue

                    x = ncout.createVariable(vardict[name], 'f4', dimsout)
                    if len(variable.dimensions) == 4:
                        ncout[vardict[name]][:] = ncin[name][0, ...]
                    elif len(variable.dimensions) == 3:
                        ncout[vardict[name]][:] = ncin[name][0, ...]
                    else:
                        ncout[vardict[name]][:] = ncin[name][:]

            # Note:  increment and guess fields have same shape
            # ps_inc is (time, lat, lon), ps_ges is {time, grid_yt, grid_xt)
            # t_inc is (time, lev, lat, lon), t_ges is (time, pfull, grid_yt, grid_xt)

            ps_inc = ncin.variables['ps'][:]
            t_inc  = ncin.variables['t'][:]
            q_inc  = ncin.variables['sphum'][:]

            ps_ges = ncges.variables['pressfc'][:]
            t_ges  = ncges.variables['tmp'][:]
            q_ges  = ncges.variables['spfh'][:]

            nc_attrs = ncges.ncattrs()
            ak = ncges.getncattr('ak')
            bk = ncges.getncattr('bk')

            ps_anl = np.zeros((nlats,nlons),float)
            ps_anl = ps_ges + ps_inc

            delp_inc = np.zeros((nlevs,nlats,nlons),float)
            k = 0
            while k < nlevs:
                dbk = bk[k+1] - bk[k]
                delp_inc[k,:,:] = ps_inc[:,:] * dbk
                k = k + 1

            x = ncout.createVariable('delp_inc','f4',dimsout4)
            ncout['delp_inc'][:] = delp_inc[:]


            t_anl = np.zeros((nlevs,nlats,nlons),float)
            q_anl = np.zeros((nlevs,nlats,nlons),float)
            t_anl = np.add(t_ges,t_inc)
            q_anl = q_ges + q_inc

            # Set constants
            rd = 2.8705e+2
            rv = 4.6150e+2
            fv = (rv/rd)-1.0
            rdog = rd/grav

            tv_ges  = np.zeros((nlevs,nlats,nlons),float)
            tv_anl  = np.zeros((nlevs,nlats,nlons),float)
            tv_ges = t_ges * (1.0 + fv*q_ges)
            tv_anl = t_anl * (1.0 + fv*q_anl)

            delz_ges = np.zeros((nlevs,nlats,nlons),float)
            delz_anl = np.zeros((nlevs,nlats,nlons),float)
            delz_inc = np.zeros((nlevs,nlats,nlons),float)

            k = 0
            while k < nlevs:
                delz_ges[k,:,:] = rdog * tv_ges[:,k,:,:] * np.log((ak[k]+bk[k]*ps_ges[:,:])/(ak[k+1]+bk[k+1]*ps_ges[:,:]))
                delz_anl[k,:,:] = rdog * tv_anl[:,k,:,:] * np.log((ak[k]+bk[k]*ps_anl[:,:])/(ak[k+1]+bk[k+1]*ps_anl[:,:]))
                delz_inc[k,:,:] = delz_anl[k,:,:] - delz_ges[k,:,:]
                k = k +1

            x = ncout.createVariable('delz_inc','f4',dimsout4)
            ncout['delz_inc'][:] = delz_inc[:]

    except FileNotFoundError as e:
        print(e)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('FV3background', type=str, help='Input FV3 background file')
    parser.add_argument('FV3JEDIincrement', type=str, help='Input FV3-JEDI LatLon Increment File')
    parser.add_argument('FV3increment', type=str, help='Output FV3 Increment File')
    args = parser.parse_args()
    jedi_inc_to_fv3(args.FV3background,args.FV3JEDIincrement,args.FV3increment)
