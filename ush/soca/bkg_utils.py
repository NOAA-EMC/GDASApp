#!/usr/bin/env python3
# Script name:         ush/soca/bkg_utils.py
# Script description:  Utilities for staging SOCA background

import dateutil.parser as dparser
from datetime import datetime, timedelta
from netCDF4 import Dataset
import numpy as np
import os
import shutil
from wxflow import (Logger, FileHandler)
import xarray as xr
import yaml
from scipy.interpolate import griddata

logger = Logger()

# get absolute path of ush/ directory either from env or relative to this file
my_dir = os.path.dirname(__file__)
my_home = os.path.dirname(os.path.dirname(my_dir))
gdas_home = os.path.join(os.getenv('HOMEgfs'), 'sorc', 'gdas.cd')


def agg_seaice(fname_in, fname_out):
    """
    Aggregates seaice variables from a CICE restart fname_in and save in fname_out.
    """

    soca2cice_vars = {'aicen': 'aicen',
                      'hicen': 'vicen',
                      'hsnon': 'vsnon'}

    # read CICE restart
    ds = xr.open_dataset(fname_in)
    nj = np.shape(ds['aicen'])[1]
    ni = np.shape(ds['aicen'])[2]

    # populate xarray with aggregated quantities
    aggds = xr.merge([xr.DataArray(
                      name=varname,
                      data=np.reshape(np.sum(ds[soca2cice_vars[varname]].values, axis=0), (1, nj, ni)),
                      dims=['time', 'yaxis_1', 'xaxis_1']) for varname in soca2cice_vars.keys()])

    # remove fill value
    encoding = {varname: {'_FillValue': False} for varname in soca2cice_vars.keys()}

    # save datasets
    aggds.to_netcdf(fname_out, format='NETCDF4', unlimited_dims='time', encoding=encoding)

    # xarray doesn't allow variables and dim that have the same name, switch to netCDF4
    ncf = Dataset(fname_out, 'a')
    t = ncf.createVariable('time', 'f8', ('time'))
    t[:] = 1.0
    ncf.close()


def cice_hist2fms(input_filename, output_filename):
    """
    Simple reformatting utility to allow soca/fms to read CICE's history
    """
    input_filename_real = os.path.realpath(input_filename)

    # open the CICE history file
    ds = xr.open_dataset(input_filename_real)

    if 'aicen' in ds.variables and 'hicen' in ds.variables and 'hsnon' in ds.variables:
        logger.info(f"*** Already reformatted, skipping.")
        return

    # rename the dimensions to xaxis_1 and yaxis_1
    ds = ds.rename({'ni': 'xaxis_1', 'nj': 'yaxis_1'})

    # rename the variables
    ds = ds.rename({'aice_h': 'aicen', 'hi_h': 'hicen', 'hs_h': 'hsnon'})

    # Save the new netCDF file
    output_filename_real = os.path.realpath(output_filename)
    ds.to_netcdf(output_filename_real, mode='w')


def test_hist_date(histfile, ref_date):
    """
    Check that the date in the MOM6 history file is the expected one for the cycle.
    TODO: Implement the same for seaice
    """

    ncf = Dataset(histfile, 'r')
    hist_date = dparser.parse(ncf.variables['time'].units, fuzzy=True) + timedelta(hours=int(ncf.variables['time'][0]))
    ncf.close()
    logger.info(f"*** history file date: {hist_date} expected date: {ref_date}")
    assert hist_date == ref_date, 'Inconsistent bkg date'

#-------------------------------------------------
# Added by K. Lukens

def sst2skint(bkg_path, bkg_file, gcyc, fcst_hr):
    """
    Replace SST background (top layer of ocean model) with skin T background (from atmosphere)
    """

    # Get paths to background files
    #tpath_bkg_ocn = str(os.getenv('COM_OCEAN_HISTORY_PREV'))
    path_bkg_ocn  = str(bkg_path)+'/' #tpath_bkg_ocn+'/'
    path_bkg_atm = path_bkg_ocn.replace('ocean', 'atmos')
    #os.system('mkdir '+str(path_bkg_atm))

    #tmpatmpath = '/scratch1/NCEPDEV/da/Katherine.Lukens/NSST/tools/sst2skinT/data/model_data/atmos/history/gdas.t'+str(gcyc)+'z.sfcf'+str(fcst_hr)+'.nc'
    tmpatmpath = '/scratch1/NCEPDEV/da/Katherine.Lukens/NSST/tools/sst2skinT/data/model_data/atmos/history/gdas.t12z.sfcf'+str(fcst_hr)+'.nc'
    os.system('cp '+str(tmpatmpath)+' '+str(path_bkg_atm))

    # Get ocean model grid
#    grid_fname = os.path.join('/scratch2/NCEPDEV/ocean/Guillaume.Vernieres/runs/low-res/soca_gridspec.nc')
    grid_fname = os.path.join('/scratch1/NCEPDEV/da/Katherine.Lukens/NSST/tools/sst2skinT/data/model_data/MOM.res.nc')
#    grid_fname = os.path.join('../../build/gdas/test/soca/gw/testrun/testjjobs/RUNDIRS/gdas_test/gdasocnanal_12/INPUT/MOM.res.nc')
    ds = xr.open_dataset(grid_fname)
#    ocnlat = np.squeeze(ds['lat'][:])
#    ocnlon = np.squeeze(ds['lon'][:])
    ocnlat = np.squeeze(ds['geolat'][:])
    ocnlon = np.squeeze(ds['geolon'][:])
    ds.close()
    	# ocean grid size
    shapelat = np.shape(ocnlat)
    nlat = shapelat[0]
    nlon = shapelat[1]

    # Get skin T background
    fskin = path_bkg_atm+'gdas.t12z.sfcf'+str(fcst_hr)+'.nc'
    #fskin = os.path.join(path_bkg_atm, f'gdas.t12z.sfcf'+str(fcst_hr)+'.nc')
    print("fskin = "+str(fskin))
    #ds     = xr.open_dataset(fskin)
    #skinT  = np.squeeze(ds['tmpsfc'][0,:,:].values) - 273.15
    #atmlat = np.squeeze(ds['grid_yt'].values)
    #atmlon = np.squeeze(ds['grid_xt'].values)
    ds     = Dataset(fskin)
    skinT  = np.array(ds.variables['tmpsfc'][0,:,:] - 273.15)
    atmlat = np.array(ds.variables['grid_yt'])
    atmlon = np.array(ds.variables['grid_xt'])
    #atmlon = ds.variables['grid_xt']
    ds.close()
    print("type atmlat = "+str(type(atmlat)))
    print("type atmlon = "+str(type(atmlon)))
    print("shape atmlat = "+str(np.shape(atmlat)))
    print("shape atmlon = "+str(np.shape(atmlon)))

    # Regrid skin T to ocean model grid
    ocnlon_max = np.max(ocnlon)
        # get atmos gaussian grid and rotate to match ocean grid
    #atmlon[atmlon >= ocnlon_max] = atmlon[atmlon >= ocnlon_max] - 360
    #atmlon = np.where(atmlon >= ocnlon_max, atmlon - 360, atmlon)
    atmlon = [atmlon[i]-360.0 if atmlon[i]>=ocnlon_max else atmlon[i] for i in range(np.size(atmlon))]

    atmlongrid, atmlatgrid = np.meshgrid(atmlon, atmlat)
        # regrid atmos variable to ocean grid
    skinT_regrid = griddata((atmlongrid.reshape(-1), atmlatgrid.reshape(-1)), np.squeeze(skinT.reshape(-1)), (ocnlon, ocnlat), method='nearest')

    # Replace SST with skin T
    # ... Add new T (with skin T) back into existing ocean background files (netcdf)
        # open ocean background file
    nc = Dataset(path_bkg_ocn+bkg_file, mode='a', format='NetCDF4 Classic')
        # mask land values in skinT_regrid
    sst = np.asarray(nc.variables['Temp'][0,0,:,:])
    for j in range(nlat-1):
      for k in range(nlon-1):
        #if sst[j,k]<0:
        if sst[j,k]<-999 or sst[j,k]>999:
          tmiss = sst[j,k]
          break
    print("sst2skint: land missing value = "+str(tmiss))
    skinT_regridmask = np.where(sst==tmiss, tmiss, skinT_regrid)
    print("sst2skint: shape regrid, regridmask = "+str(np.shape(skinT_regrid))+" "+str(np.shape(skinT_regridmask)))
    print("sst2skint: min, max regrid = "+str(np.min(skinT_regrid))+" "+str(np.max(skinT_regrid)))
    print("sst2skint: min, max regridmask = "+str(np.min(skinT_regridmask))+" "+str(np.max(skinT_regridmask)))
        # replace SST with skinT
    nc['Temp'][0,0,:,:] = skinT_regridmask[:,:]
    newncT = np.asarray(nc.variables['Temp'])

    nc.close()

#-------------------------------------------------

def gen_bkg_list(bkg_path, out_path, window_begin=' ', yaml_name='bkg.yaml', ice_rst=False):
    """
    Generate a YAML of the list of backgrounds for the pseudo model
    """

    # Pseudo model parameters (time step, start date)
    # TODO: make this a parameter
    dt_pseudo = 3
    bkg_date = window_begin

    # Construct list of background file names
    RUN = os.getenv('RUN')
    cyc = str(os.getenv('cyc')).zfill(2)
    gcyc = str((int(cyc) - 6) % 24).zfill(2)  # previous cycle
    fcst_hrs = list(range(3, 10, dt_pseudo))
    files = []
    for fcst_hr in fcst_hrs:
        files.append(os.path.join(bkg_path, f'{RUN}.ocean.t'+gcyc+'z.inst.f'+str(fcst_hr).zfill(3)+'.nc'))

	#------------------------------------------------------
	# K. Lukens:
 	# Add SST-to-skinT function call here
		# make a copy of the background file
        #os.system('cp '+str(bkg_path)+'{RUN}.ocean.t'+gcyc+'z.inst.f'+str(fcst_hr).zfill(3)+'.nc {RUN}.ocean.t'+gcyc+'z.inst.f'+str(fcst_hr).zfill(3)+'_CP.nc')

                # create /atmos/history/ directory
        path_bkg_ocn = str(bkg_path)+'/' #tpath_bkg_ocn+'/'
        path_bkg_atm = path_bkg_ocn.replace('ocean', 'atmos')
        os.system('mkdir -p '+str(path_bkg_atm))

                # replace SST background with skin T background in the existing netcdf file
        bkg_file = str(RUN)+'.ocean.t'+str(gcyc)+'z.inst.f'+str(fcst_hr).zfill(3)+'.nc'
        sst2skint(bkg_path, bkg_file, gcyc, str(fcst_hr).zfill(3))
	#------------------------------------------------------

    # Identify the ocean background that will be used for the  vertical coordinate remapping
    ocn_filename_ic = os.path.splitext(os.path.basename(files[0]))[0]+'.nc'
    test_hist_date(os.path.join(bkg_path, ocn_filename_ic), bkg_date)  # assert date of the history file is correct

    # Copy/process backgrounds and generate background yaml list
    bkg_list_src_dst = []
    bkg_list = []
    for bkg in files:

        # assert validity of the ocean bkg date, remove basename
        test_hist_date(bkg, bkg_date)
        ocn_filename = os.path.splitext(os.path.basename(bkg))[0]+'.nc'

        # prepare the seaice background, aggregate if the backgrounds are CICE restarts
        ice_filename = ocn_filename.replace("ocean", "ice")
        agg_ice_filename = ocn_filename.replace("ocean", "agg_ice")
        if ice_rst:
            # if this is a CICE restart, aggregate seaice variables and dump
            # aggregated ice bkg in out_path
            # TODO: This option is turned off for now, figure out what to do with it.
            agg_seaice(os.path.join(bkg_path, ice_filename),
                       os.path.join(out_path, agg_ice_filename))
        else:
            # Process the CICE history file so they can be read by soca/fms
            # TODO: Add date check of the cice history
            # TODO: bkg_path should be 1 level up
            cice_hist2fms(os.path.join(os.getenv('COM_ICE_HISTORY_PREV'), ice_filename),
                          os.path.join(out_path, agg_ice_filename))

        # prepare list of ocean bkg to be copied to RUNDIR
        bkg_list_src_dst.append([os.path.join(bkg_path, ocn_filename),
                                 os.path.join(out_path, ocn_filename)])

        bkg_dict = {'date': bkg_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'basename': './bkg/',
                    'ocn_filename': ocn_filename,
                    'ice_filename': agg_ice_filename,
                    'read_from_file': 1}

        bkg_date = bkg_date + timedelta(hours=dt_pseudo)  # TODO: make the bkg interval a configurable
        bkg_list.append(bkg_dict)

    # save pseudo model yaml configuration
    f = open(yaml_name, 'w')
    yaml.dump(bkg_list[1:], f, sort_keys=False, default_flow_style=False)

    # copy ocean backgrounds to RUNDIR
    FileHandler({'copy': bkg_list_src_dst}).sync()


def stage_ic(bkg_dir, anl_dir, RUN, gcyc):

    # Copy and rename initial condition
    ics_list = []
    # ocean IC's
    mom_ic_src = os.path.join(bkg_dir, f'{RUN}.ocean.t{gcyc}z.inst.f003.nc')
    mom_ic_dst = os.path.join(anl_dir, 'INPUT', 'MOM.res.nc')
    ics_list.append([mom_ic_src, mom_ic_dst])

    # seaice IC's
    cice_ic_src = os.path.join(bkg_dir, f'{RUN}.agg_ice.t{gcyc}z.inst.f003.nc')
    cice_ic_dst = os.path.join(anl_dir, 'INPUT', 'cice.res.nc')
    ics_list.append([cice_ic_src, cice_ic_dst])

    #------------------------------------------------------
    # K. Lukens:
    # Add SST-to-skinT function call here
            # make a copy of the background file
    #mom_ic_src_cp = os.path.join(bkg_dir, f'{RUN}.ocean.t{gcyc}z.inst.f003_CP.nc')
    #os.system('cp '+str(mom_ic_src)+' '+str(mom_ic_src_cp))

            # create /atmos/history/ directory
    #path_bkg_ocn = str(bkg_dir)+'/' #tpath_bkg_ocn+'/'
    #path_bkg_atm = path_bkg_ocn.replace('ocean', 'atmos')
    #os.system('mkdir -p '+str(path_bkg_atm))

            # replace SST background with skin T background in the existing netcdf file
    bkg_file = f'{RUN}.ocean.t{gcyc}z.inst.f003.nc'
    sst2skint(bkg_dir, bkg_file, gcyc, '003')
    #------------------------------------------------------

    FileHandler({'copy': ics_list}).sync()
