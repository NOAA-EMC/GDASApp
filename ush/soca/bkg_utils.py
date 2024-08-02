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


def gen_bkg_list(bkg_path, out_path, window_begin=' ', yaml_name='bkg.yaml', ice_rst=False):
    """
    Generate a YAML of the list of backgrounds for the pseudo model
    """

    # Pseudo model parameters (time step, start date)
    # TODO: make this a parameter
    dt_pseudo = 3
    bkg_date = window_begin

    # Construct list of background file names
    cyc = str(os.getenv('cyc')).zfill(2)
    gcyc = str((int(cyc) - 6) % 24).zfill(2)  # previous cycle
    fcst_hrs = list(range(3, 10, dt_pseudo))
    files = []
    for fcst_hr in fcst_hrs:
        files.append(os.path.join(bkg_path, f'gdas.ocean.t'+gcyc+'z.inst.f'+str(fcst_hr).zfill(3)+'.nc'))

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

        # prepare list of ocean and ice bkg to be copied to RUNDIR
        bkg_list_src_dst.append([os.path.join(bkg_path, ocn_filename),
                                 os.path.join(out_path, ocn_filename)])
        bkg_list_src_dst.append([os.path.join(os.getenv('COM_ICE_HISTORY_PREV'), ice_filename),
                                 os.path.join(out_path, ice_filename)])

        bkg_dict = {'date': bkg_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'basename': './bkg/',
                    'ocn_filename': ocn_filename,
                    'ice_filename': ice_filename,
                    'read_from_file': 1}

        bkg_date = bkg_date + timedelta(hours=dt_pseudo)  # TODO: make the bkg interval a configurable
        bkg_list.append(bkg_dict)

    # save pseudo model yaml configuration
    f = open(yaml_name, 'w')
    yaml.dump(bkg_list[1:], f, sort_keys=False, default_flow_style=False)

    # copy ocean backgrounds to RUNDIR
    FileHandler({'copy': bkg_list_src_dst}).sync()


def stage_ic(bkg_dir, anl_dir, gcyc):

    # Copy and rename initial condition
    ics_list = []
    # ocean IC's
    mom_ic_src = os.path.join(bkg_dir, f'gdas.ocean.t{gcyc}z.inst.f003.nc')
    mom_ic_dst = os.path.join(anl_dir, 'INPUT', 'MOM.res.nc')
    ics_list.append([mom_ic_src, mom_ic_dst])

    # seaice IC's
    cice_ic_src = os.path.join(bkg_dir, f'gdas.ice.t{gcyc}z.inst.f003.nc')
    cice_ic_dst = os.path.join(anl_dir, 'INPUT', 'cice.res.nc')
    ics_list.append([cice_ic_src, cice_ic_dst])
    FileHandler({'copy': ics_list}).sync()
