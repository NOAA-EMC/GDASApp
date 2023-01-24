#!/usr/bin/env python3
################################################################################
#  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exufsda_global_marine_analysis_vrfy.py
# Script description:  State and observation space verification for UFS Global Marine Analysis
#
# Author: Guillaume Vernieres      Org: NCEP/EMC     Date: 2023-01-23
#
# Abstract: This script produces a figures relevant to the cycle
#
# $Id$
#
# Attributes:
#   Language: Python3
#
################################################################################

# import os and sys to add ush to path
import os
import sys
import yaml
import glob
import dateutil.parser as dparser
import shutil

import subprocess
from datetime import datetime, timedelta
from netCDF4 import Dataset
import xarray as xr
import numpy as np
import logging

# set up logger
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

import xarray as xr
import matplotlib.pyplot as plt

import xarray as xr
import cartopy
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import ufsda


def plot_config(grid_file, data_file, variable, levels, bounds, colormap, comout):
    """
    Prepares the configuration for the plotting function below
    """
    config = {}
    config['grid file'] = grid_file
    config['fields file'] = data_file
    config['variable'] = variable
    config['levels'] = levels
    config['bounds'] = bounds
    config['colormap'] = colormap
    config['comout'] = comout
    return config


def plot_horizontal_slice(config):
    """
    pcolormesh of a horizontal slice of an ocean field
    """
    level = config['levels'][0]
    grid = xr.open_dataset(config['grid file'])
    data = xr.open_dataset(config['fields file'])
    if config['variable'] in ['Temp', 'Salt', 'u', 'v']:
        slice_data = data[config['variable']].sel(Layer=level)
    else:
        slice_data = data[config['variable']]
    bounds = config['bounds']
    fig, ax = plt.subplots(figsize=(8, 5), subplot_kw={'projection': ccrs.PlateCarree()})
    plt.pcolormesh(np.squeeze(grid.lon),
                   np.squeeze(grid.lat),
                   np.squeeze(slice_data),
                   vmin=bounds[0], vmax=bounds[1],
                   transform=ccrs.PlateCarree(),
                   cmap=config['colormap'])
    plt.colorbar(label=config['variable']+' Level '+str(level), shrink=0.5, orientation='horizontal')
    ax.coastlines()
    ax.gridlines(draw_labels=True)
    ax.add_feature(cartopy.feature.LAND)
    dirname = os.path.join(config['comout'], 'vrfy', config['variable'])
    ufsda.mkdir(dirname)
    figname = os.path.join(dirname, config['variable']+'_Level_'+str(level))
    plt.savefig(figname, bbox_inches='tight')


comout = os.getenv('COMOUT')

# Temperature
config = plot_config(grid_file=os.path.join(comout, 'gdas.t9z.ocngrid.nc'),
                     data_file=os.path.join(comout, 'gdas.t12z.ocninc.nc'),
                     variable='Temp',
                     levels=[1],
                     bounds=[-1, 1],
                     colormap='bwr',
                     comout=comout)
plot_horizontal_slice(config)

# Salinity
config['variable'] = 'Salt'
config['bounds'] = [-0.1, 0.1]
plot_horizontal_slice(config)

# Sea surface height
config['variable'] = 'ave_ssh'
config['bounds'] = [-0.1, 0.1]
plot_horizontal_slice(config)
