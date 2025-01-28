#!/usr/bin/env python3

# make plots for marine analysis

import matplotlib.pyplot as plt
import xarray as xr
import cartopy
import cartopy.crs as ccrs
import numpy as np
import os


projs = {'North': ccrs.NorthPolarStereo(),
         'South': ccrs.SouthPolarStereo(),
         'Global': ccrs.Mollweide(central_longitude=-150)}


def plotConfig(grid_file=[],
               data_file=[],
               layer_file=[],
               variable=[],
               PDY=os.getenv('PDY'),
               cyc=os.getenv('cyc'),
               exp=os.getenv('PSLOT'),
               levels=[],
               bounds=[],
               colormap=[],
               max_depth=np.nan,
               max_depths=[700.0, 5000.0],
               comout=[],
               variables_horiz={},
               variables_zonal={},
               variables_meridional={},
               lat=np.nan,
               lats=np.arange(-60, 60, 10),
               lon=np.nan,
               lons=np.arange(-280, 80, 30),
               proj='set me',
               projs=['Global']):

    # Map variable names to their units
    variable_units = {
        'ave_ssh': 'meter',
        'Temp': 'deg C',
        'Salt': 'psu',
        'aice_h': 'unitless',
        'hi_h': 'meter',
        'hs_h': 'meter',
        'u': 'm/s',
        'v': 'm/s'
    }

    """
    Prepares the configuration for the plotting functions below
    """
    config = {}
    config['comout'] = comout  # output directory
    config['grid file'] = grid_file
    config['fields file'] = data_file
    config['layer file'] = layer_file
    config['PDY'] = PDY
    config['cyc'] = cyc
    config['exp'] = exp
    config['levels'] = [1]
    config['colormap'] = colormap
    config['bounds'] = bounds
    config['lats'] = lats  # all the lats to plot
    config['lat'] = lat  # the lat being currently plotted
    config['lons'] = lons  # all the lons to plot
    config['lon'] = lon  # the lon being currently plotted
    config['max depths'] = max_depths  # all the max depths to plot
    config['max depth'] = max_depth  # the max depth currently plotted
    config['horiz variables'] = variables_horiz  # all the vars for horiz plots
    config['zonal variables'] = variables_zonal  # all the vars for zonal plots
    config['meridional variables'] = variables_meridional  # all the vars for meridional plots
    config['variable'] = variable  # the variable currently plotted
    config['projs'] = projs  # all the projections etc.
    config['proj'] = proj

    # Add units to the config for each variable
    config['variable_units'] = variable_units
    return config


def plotHorizontalSlice(config):
    """
    Contourf of a horizontal slice of an ocean field
    """
    grid = xr.open_dataset(config['grid file'])
    data = xr.open_dataset(config['fields file'])

    dirname = os.path.join(config['comout'], config['variable'])
    os.makedirs(dirname, exist_ok=True)

    variable = config['variable']
    unit = config['variable_units'].get(config['variable'], 'unknown')
    exp = config['exp']
    PDY = config['PDY']
    cyc = config['cyc']

    if variable in ['Temp', 'Salt', 'u', 'v']:
        level = config['levels'][0]
        slice_data = np.squeeze(data[variable])[level, :, :]
        label_colorbar = f"{variable} ({unit}) Level {level}"
        figname = os.path.join(dirname, variable + '_Level_' + str(level))
        title = f"{exp} {PDY} {cyc} {variable} Level {level}"
    else:
        slice_data = np.squeeze(data[variable])
        label_colorbar = f"{variable} ({unit})"
        figname = os.path.join(dirname, variable + '_' + config['proj'])
        title = f"{exp} {PDY} {cyc} {variable}"

    bounds = config['horiz variables'][variable]
    slice_data = np.clip(slice_data, bounds[0], bounds[1])

    fig, ax = plt.subplots(figsize=(8, 5), subplot_kw={'projection': projs[config['proj']]})

    # Use pcolor to plot the data
    pcolor_plot = ax.pcolormesh(np.squeeze(grid.lon),
                                np.squeeze(grid.lat),
                                slice_data,
                                vmin=bounds[0], vmax=bounds[1],
                                transform=ccrs.PlateCarree(),
                                cmap=config['colormap'],
                                zorder=0)

    # Add colorbar for filled contours
    cbar = fig.colorbar(pcolor_plot, ax=ax, shrink=0.75, orientation='horizontal')
    cbar.set_label(label_colorbar)

    # Add contour lines with specified linewidths
    contour_levels = np.linspace(bounds[0], bounds[1], 5)
    ax.contour(np.squeeze(grid.lon),
               np.squeeze(grid.lat),
               slice_data,
               levels=contour_levels,
               colors='black',
               linewidths=0.1,
               transform=ccrs.PlateCarree(),
               zorder=2)

    try:
        ax.coastlines()  # TODO: make this work on hpc
    except Exception as e:
        print(f"Warning: could not add coastlines. {e}")
    ax.set_title(title)
    if config['proj'] == 'South':
        ax.set_extent([-180, 180, -90, -50], ccrs.PlateCarree())
    if config['proj'] == 'North':
        ax.set_extent([-180, 180, 50, 90], ccrs.PlateCarree())
    # ax.add_feature(cartopy.feature.LAND)  # TODO: make this work on hpc
    plt.savefig(figname, bbox_inches='tight', dpi=300)
    plt.close(fig)


def plotZonalSlice(config):
    """
    Contourf of a zonal slice of an ocean field
    """
    variable = config['variable']
    unit = config['variable_units'].get(config['variable'], 'unknown')
    exp = config['exp']
    PDY = config['PDY']
    cyc = config['cyc']
    lat = float(config['lat'])
    grid = xr.open_dataset(config['grid file'])
    data = xr.open_dataset(config['fields file'])
    layer = xr.open_dataset(config['layer file'])
    lat_index = np.argmin(np.array(np.abs(np.squeeze(grid.lat)[:, 0] - lat)))
    slice_data = np.squeeze(np.array(data[variable]))[:, lat_index, :]
    depth = np.squeeze(np.array(layer['h']))[:, lat_index, :]
    depth[np.where(np.abs(depth) > 10000.0)] = 0.0
    depth = np.cumsum(depth, axis=0)
    bounds = config['zonal variables'][variable]
    slice_data = np.clip(slice_data, bounds[0], bounds[1])
    x = np.tile(np.squeeze(grid.lon[:, lat_index]), (np.shape(depth)[0], 1))

    fig, ax = plt.subplots(figsize=(8, 5))

    # Plot the filled contours
    contourf_plot = ax.contourf(x, -depth, slice_data,
                                levels=np.linspace(bounds[0], bounds[1], 100),
                                vmin=bounds[0], vmax=bounds[1],
                                cmap=config['colormap'])

    # Add contour lines with specified linewidths
    contour_levels = np.linspace(bounds[0], bounds[1], 5)
    ax.contour(x, -depth, slice_data,
               levels=contour_levels,
               colors='black',
               linewidths=0.1)

    # Add colorbar for filled contours
    cbar = fig.colorbar(contourf_plot, ax=ax, shrink=0.5, orientation='horizontal')
    cbar.set_label(f"{config['variable']} ({unit}) Lat {lat}")

    # Set the colorbar ticks
    cbar.set_ticks(contour_levels)
    contourf_plot.set_clim(bounds[0], bounds[1])

    ax.set_ylim(-config['max depth'], 0)
    title = f"{exp} {PDY} {cyc} {variable} lat {int(lat)}"
    ax.set_title(title)
    dirname = os.path.join(config['comout'], config['variable'])
    os.makedirs(dirname, exist_ok=True)
    figname = os.path.join(dirname, config['variable'] +
                           'zonal_lat_' + str(int(lat)) + '_' + str(int(config['max depth'])) + 'm')
    plt.savefig(figname, bbox_inches='tight', dpi=300)
    plt.close(fig)


def plotMeridionalSlice(config):
    """
    Contourf of a Meridional slice of an ocean field
    """
    variable = config['variable']
    unit = config['variable_units'].get(config['variable'], 'unknown')
    exp = config['exp']
    PDY = config['PDY']
    cyc = config['cyc']
    lon = float(config['lon'])
    grid = xr.open_dataset(config['grid file'])
    data = xr.open_dataset(config['fields file'])
    layer = xr.open_dataset(config['layer file'])
    lon_index = np.argmin(np.array(np.abs(np.squeeze(grid.lon)[0, :] - lon)))
    slice_data = np.squeeze(np.array(data[config['variable']]))[:, :, lon_index]
    depth = np.squeeze(np.array(layer['h']))[:, :, lon_index]
    depth[np.where(np.abs(depth) > 10000.0)] = 0.0
    depth = np.cumsum(depth, axis=0)
    bounds = config['meridional variables'][variable]
    slice_data = np.clip(slice_data, bounds[0], bounds[1])
    y = np.tile(np.squeeze(grid.lat)[:, lon_index], (np.shape(depth)[0], 1))

    fig, ax = plt.subplots(figsize=(8, 5))

    # Plot the filled contours
    contourf_plot = ax.contourf(y, -depth, slice_data,
                                levels=np.linspace(bounds[0], bounds[1], 100),
                                vmin=bounds[0], vmax=bounds[1],
                                cmap=config['colormap'])

    # Add contour lines with specified linewidths
    contour_levels = np.linspace(bounds[0], bounds[1], 5)
    ax.contour(y, -depth, slice_data,
               levels=contour_levels,
               colors='black',
               linewidths=0.1)

    # Add colorbar for filled contours
    cbar = fig.colorbar(contourf_plot, ax=ax, shrink=0.5, orientation='horizontal')
    cbar.set_label(f"{config['variable']} ({unit}) Lon {lon}")

    # Set the colorbar ticks
    cbar.set_ticks(contour_levels)
    contourf_plot.set_clim(bounds[0], bounds[1])

    ax.set_ylim(-config['max depth'], 0)
    title = f"{exp} {PDY} {cyc} {variable} lon {int(lon)}"
    ax.set_title(title)
    dirname = os.path.join(config['comout'], config['variable'])
    os.makedirs(dirname, exist_ok=True)
    figname = os.path.join(dirname, config['variable'] +
                           'meridional_lon_' + str(int(lon)) + '_' + str(int(config['max depth'])) + 'm')
    plt.savefig(figname, bbox_inches='tight', dpi=300)
    plt.close(fig)


class statePlotter:

    def __init__(self, config_dict):
        self.config = config_dict

    def plot(self):
        # Loop over variables, slices (horiz and vertical) and projections ... and whatever else is needed

        #######################################
        # zonal slices

        for lat in self.config['lats']:
            self.config['lat'] = lat

            for max_depth in self.config['max depths']:
                self.config['max depth'] = max_depth

                variableBounds = self.config['zonal variables']
                for variable in variableBounds.keys():
                    bounds = variableBounds[variable]
                    self.config.update({'variable': variable, 'bounds': bounds})
                    plotZonalSlice(self.config)

        #######################################
        # Meridional slices

        for lon in self.config['lons']:
            self.config['lon'] = lon

            for max_depth in self.config['max depths']:
                self.config['max depth'] = max_depth

                variableBounds = self.config['meridional variables']
                for variable in variableBounds.keys():
                    bounds = variableBounds[variable]
                    self.config.update({'variable': variable, 'bounds': bounds})
                    plotMeridionalSlice(self.config)

        #######################################
        # Horizontal slices
        for proj in self.config['projs']:

            variableBounds = self.config['horiz variables']
            for variable in variableBounds.keys():
                bounds = variableBounds[variable]
                self.config.update({'variable': variable, 'bounds': bounds, 'proj': proj})
                plotHorizontalSlice(self.config)
