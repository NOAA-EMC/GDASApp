#!/usr/bin/env python3
################################################################################
#  UNIX Script Documentation Block
#                      .                                             .
# Script name:         soca_vrfy.py
# Script description:  Module with plotting functions for marine analysis vrfy task
#
# Author: Andrew Eichmann          Org: NCEP/EMC     Date: 2023-07-13
#
# Abstract: This script produces figures relevant to the marine DA cycle
#
# $Id$
#
# Attributes:
#   Language: Python3
#
################################################################################


import matplotlib.pyplot as plt
import xarray as xr
import cartopy
import cartopy.crs as ccrs
import numpy as np
import os


projs = {'North': ccrs.NorthPolarStereo(),
         'South': ccrs.SouthPolarStereo(),
         'Global': ccrs.Mollweide(central_longitude=-150)}


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
    config['proj'] = 'Global'
    return config


def plot_horizontal_slice(config):
    """
    pcolormesh of a horizontal slice of an ocean field
    """
    grid = xr.open_dataset(config['grid file'])
    data = xr.open_dataset(config['fields file'])

    dirname = os.path.join(config['comout'], config['variable'])
    os.makedirs(dirname, exist_ok=True)

    if config['variable'] in ['Temp', 'Salt', 'u', 'v']:
        level = config['levels'][0]
        slice_data = np.squeeze(data[config['variable']])[level, :, :]
        label_colorbar = config['variable']+' Level '+str(level)
        figname = os.path.join(dirname, config['variable']+'_Level_'+str(level))
    else:
        slice_data = np.squeeze(data[config['variable']])
        label_colorbar = config['variable']
        figname = os.path.join(dirname, config['variable']+'_'+config['proj'])

    bounds = config['bounds']

    fig, ax = plt.subplots(figsize=(8, 5), subplot_kw={'projection': projs[config['proj']]})
    plt.pcolormesh(np.squeeze(grid.lon),
                   np.squeeze(grid.lat),
                   slice_data,
                   vmin=bounds[0], vmax=bounds[1],
                   transform=ccrs.PlateCarree(),
                   cmap=config['colormap'])

    plt.colorbar(label=label_colorbar, shrink=0.5, orientation='horizontal')
    ax.coastlines()  # TODO: make this work on hpc
    ax.gridlines(draw_labels=True)
    if config['proj'] == 'South':
        ax.set_extent([-180, 180, -90, -50], ccrs.PlateCarree())
    if config['proj'] == 'North':
        ax.set_extent([-180, 180, 50, 90], ccrs.PlateCarree())
    # ax.add_feature(cartopy.feature.LAND)  # TODO: make this work on hpc
    plt.savefig(figname, bbox_inches='tight', dpi=600)


def plot_zonal_slice(config):
    """
    pcolormesh of a zonal slice of an ocean field
    """
    lat = float(config['lats'][0])
    grid = xr.open_dataset(config['grid file'])
    data = xr.open_dataset(config['fields file'])
    lat_index = np.argmin(np.array(np.abs(np.squeeze(grid.lat)[:, 0]-lat)))
    slice_data = np.squeeze(np.array(data[config['variable']]))[:, lat_index, :]
    depth = np.squeeze(np.array(grid['h']))[:, lat_index, :]
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
    os.makedirs(dirname, exist_ok=True)
    figname = os.path.join(dirname, config['variable'] +
                           'zonal_lat_'+str(int(lat)) + '_' + str(int(config['max depth'])) + 'm')
    plt.savefig(figname, bbox_inches='tight', dpi=600)
