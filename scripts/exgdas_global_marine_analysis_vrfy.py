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


def plot_config(grid_file=[], data_file=[],
                variable=[], levels=[], bounds=[], colormap=[], comout=[], lats=[]):
    """
    Prepares the configuration for the plotting functions below
    """
    config = {}
    config['grid file'] = grid_file
    config['fields file'] = data_file
    config['variable'] = variable
    config['levels'] = levels
    config['bounds'] = bounds
    config['colormap'] = colormap
    config['lats'] = lats
    config['comout'] = comout
    config['max depth'] = 5000.0
    return config


def plot_horizontal_slice(config):
    """
    pcolormesh of a horizontal slice of an ocean field
    """
    level = config['levels'][0]
    grid = xr.open_dataset(config['grid file'])
    data = xr.open_dataset(config['fields file'])
    if config['variable'] in ['Temp', 'Salt', 'u', 'v']:
        slice_data = np.squeeze(data[config['variable']])[level, :, :]
    else:
        slice_data = np.squeeze(data[config['variable']])
    bounds = config['bounds']
    fig, ax = plt.subplots(figsize=(8, 5), subplot_kw={'projection': ccrs.PlateCarree()})
    plt.pcolormesh(np.squeeze(grid.lon),
                   np.squeeze(grid.lat),
                   slice_data,
                   vmin=bounds[0], vmax=bounds[1],
                   transform=ccrs.PlateCarree(),
                   cmap=config['colormap'])
    plt.colorbar(label=config['variable']+' Level '+str(level), shrink=0.5, orientation='horizontal')
    ax.coastlines()
    ax.gridlines(draw_labels=True)
    ax.add_feature(cartopy.feature.LAND)
    dirname = os.path.join(config['comout'], config['variable'])
    ufsda.mkdir(dirname)
    figname = os.path.join(dirname, config['variable']+'_Level_'+str(level))
    plt.savefig(figname, bbox_inches='tight')


def plot_zonal_slice(config):
    """
    pcolormesh of a zonal slice of an ocean field
    """
    lat = float(config['lats'][0])
    grid = xr.open_dataset(config['grid file'])
    data = xr.open_dataset(config['fields file'])
    lat_index = np.argmin(np.array(np.abs(np.squeeze(grid.lat)[:, 0]-lat)))
    slice_data = np.squeeze(np.array(data[config['variable']].sel(yaxis_1=lat_index)))
    depth = np.squeeze(np.array(grid['h'].sel(yaxis_1=lat_index)))
    depth[np.where(np.abs(depth) > 10000.0)] = 0.0
    depth = np.cumsum(depth, axis=0)
    bounds = config['bounds']
    x = np.tile(np.squeeze(grid.lon[:, lat_index]), (np.shape(depth)[0], 1))
    fig, ax = plt.subplots(figsize=(8, 5))
    plt.pcolormesh(x, -depth, slice_data,
                   vmin=bounds[0], vmax=bounds[1],
                   cmap=config['colormap'])
    plt.colorbar(label=config['variable']+' Lat '+str(lat), shrink=0.5, orientation='horizontal')
    ax.set_ylim(-config['max depth'], 0)
    dirname = os.path.join(config['comout'], config['variable'])
    ufsda.mkdir(dirname)
    figname = os.path.join(dirname, config['variable'] +
                           'zonal_lat_'+str(int(lat)) + '_' + str(int(config['max depth'])) + 'm')
    plt.savefig(figname, bbox_inches='tight')


comout = os.getenv('COMOUT')
cyc = os.getenv('cyc')
bcyc = str((int(cyc) - 3) % 24)

grid_file = os.path.join(comout, 'gdas.t'+bcyc+'z.ocngrid.nc')

#######################################
# INCREMENT
#######################################
incr_cmap = 'RdBu'
data_file = os.path.join(comout, 'gdas.t'+cyc+'z.ocninc.nc')
config = plot_config(grid_file=grid_file,
                     data_file=data_file,
                     colormap=incr_cmap,
                     comout=os.path.join(comout, 'vrfy', 'incr'))

#######################################
# zonal slices

for lat in np.arange(-60, 60, 10):

    for max_depth in [700.0, 5000.0]:
        config['lats'] = [lat]
        config['max depth'] = max_depth

        # Temperature
        config.update({'variable': 'Temp', 'levels': [1], 'bounds': [-.5, .5]})
        plot_zonal_slice(config)

        # Salinity
        config.update({'variable': 'Salt', 'levels': [1], 'bounds': [-.1, .1]})
        plot_zonal_slice(config)

#######################################
# Horizontal slices

# Temperature
config.update({'variable': 'Temp', 'levels': [1], 'bounds': [-1, 1]})
plot_horizontal_slice(config)

# Salinity
config.update({'variable': 'Salt', 'bounds': [-0.1, 0.1]})
plot_horizontal_slice(config)

# Sea surface height
config.update({'variable': 'ave_ssh', 'bounds': [-0.1, 0.1]})
plot_horizontal_slice(config)

#######################################
# Std Bkg. Error
#######################################
bmat_cmap = 'hot'
data_file = os.path.join(comout, 'gdas.t'+cyc+'z.ocn.bkgerr_stddev.nc')
config = plot_config(grid_file=grid_file,
                     data_file=data_file,
                     colormap=bmat_cmap,
                     comout=os.path.join(comout, 'vrfy', 'bkgerr'))

#######################################
# zonal slices

for lat in np.arange(-60, 60, 10):

    for max_depth in [700.0, 5000.0]:
        config['lats'] = [lat]
        config['max depth'] = max_depth

        # Temperature
        config.update({'variable': 'Temp', 'levels': [1], 'bounds': [0, 1.5]})
        plot_zonal_slice(config)

        # Salinity
        config.update({'variable': 'Salt', 'levels': [1], 'bounds': [0, .2]})
        plot_zonal_slice(config)

#######################################
# Horizontal slices

# Temperature
config.update({'variable': 'Temp', 'levels': [1], 'bounds': [0, 2]})
plot_horizontal_slice(config)

# Salinity
config.update({'variable': 'Salt', 'bounds': [0, 0.2]})
plot_horizontal_slice(config)

# Sea surface height
config.update({'variable': 'ave_ssh', 'bounds': [0, 0.1]})
plot_horizontal_slice(config)
