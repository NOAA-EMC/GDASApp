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


def plot_config(grid_file=[],
                data_file=[],
                variable=[],
                levels=[],
                allbounds=[],
                bounds=[],
                colormap=[],
                max_depth=np.nan,
                max_depths = [700.0, 5000.0],
                comout=[],
                variables_horiz = [],
                variables_zonal = [],
                lat=np.nan,
                lats=np.arange(-60, 60, 10)):

    """
    Prepares the configuration for the plotting functions below
    """
    config = {}
    config['grid file'] = grid_file
    config['fields file'] = data_file
    config['variable'] = variable
    config['levels'] = [1]
    config['bounds'] = bounds
    config['all bounds'] = allbounds
    config['colormap'] = colormap
    config['lats'] = lats # all the lats to plot
    config['lat'] = lat  # the lat being currently plotted
    config['comout'] = comout
    config['max depth'] = max_depth
    config['max depths'] = max_depths
    config['horiz variables'] = variables_horiz
    config['zonal variables'] = variables_zonal
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
    lat = float(config['lat'])
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


def plot_increment(comout, cyc, RUN, grid_file):

    incr_cmap = 'RdBu'
    data_file = os.path.join(comout, f'{RUN}.t'+cyc+'z.ocninc.nc')
    config = plot_config(grid_file=grid_file,
                         data_file=data_file,
                         colormap=incr_cmap,
                         comout=os.path.join(comout, 'vrfy', 'incr'))

    #######################################
    # zonal slices

    for lat in np.arange(-60, 60, 10):

        for max_depth in [700.0, 5000.0]:
            config['lat'] = lat
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
    # Sea ice
    data_file = os.path.join(comout, f'{RUN}.t'+cyc+'z.ice.incr.nc')
    config = plot_config(grid_file=grid_file,
                         data_file=data_file,
                         colormap=incr_cmap,
                         comout=os.path.join(comout, 'vrfy', 'incr'))

    for proj in ['North', 'South']:
        # concentration
        config.update({'variable': 'aicen', 'bounds': [-0.2, 0.2], 'proj': proj})
        plot_horizontal_slice(config)

        # thickness
        config.update({'variable': 'hicen', 'bounds': [-0.5, 0.5], 'proj': proj})
        plot_horizontal_slice(config)

        # snow depth
        config.update({'variable': 'hsnon', 'bounds': [-0.1, 0.1], 'proj': proj})
        plot_horizontal_slice(config)


def plot_analysis(comout,
                  com_ice_history,
                  com_ocean_history,
                  cyc,
                  RUN,
                  grid_file,
                  gcyc):

    #######################################
    # Sea ice
    data_files = [os.path.join(comout, f'{RUN}.t{cyc}z.iceana.nc'),
                  os.path.join(com_ice_history, f'{RUN}.t{gcyc}z.icef006.nc')]
    dirs_out = ['ana', 'bkg']
    ice_vars = {'bkg': ['aice_h', 'hs_h', 'hi_h'], 'ana': ['aicen', 'hicen', 'hsnon']}
    for data_file, dir_out in zip(data_files, dirs_out):
        config = plot_config(grid_file=grid_file,
                             data_file=data_file,
                             colormap='jet',
                             comout=os.path.join(comout, 'vrfy', dir_out))

        for proj in ['North', 'South', 'Global']:
            # concentration
            var = ice_vars[dir_out]
            config.update({'variable': var[0], 'bounds': [0.0, 1.0], 'proj': proj})
            plot_horizontal_slice(config)

            # thickness
            config.update({'variable': var[1], 'bounds': [0.0, 4.0], 'proj': proj})
            plot_horizontal_slice(config)

            # snow depth
            config.update({'variable': var[2], 'bounds': [0.0, 0.5], 'proj': proj})
            plot_horizontal_slice(config)

    #######################################
    # Ocean surface
    data_files = [os.path.join(comout, f'{RUN}.t'+cyc+'z.ocnana.nc'),
                  os.path.join(com_ocean_history, f'{RUN}.t{gcyc}z.ocnf006.nc')]
    dirs_out = ['ana', 'bkg']
    ocn_vars = ['ave_ssh', 'Temp', 'Salt']
    for data_file, dir_out in zip(data_files, dirs_out):
        config = plot_config(grid_file=grid_file,
                             data_file=data_file,
                             colormap='jet',
                             comout=os.path.join(comout, 'vrfy', dir_out))

        # ssh
        config.update({'variable': 'ave_ssh', 'bounds': [-1.8, 1.3], 'proj': proj, 'levels': [1]})
        plot_horizontal_slice(config)

        # sst
        config.update({'variable': 'Temp', 'bounds': [-1.8, 34.0], 'proj': proj, 'levels': [1]})
        plot_horizontal_slice(config)

        # sss
        config.update({'variable': 'Salt', 'bounds': [30, 38], 'proj': proj, 'levels': [1]})
        plot_horizontal_slice(config)

#def plot_error(comout,
#                  com_ice_history,
#                  com_ocean_history,
#                  cyc,
#                  RUN,
#                  grid_file,
#                  gcyc):

#   #######################################
#    # Std Bkg. Error
#    #######################################
#    bmat_cmap = 'jet'
#    data_file = os.path.join(comout, f'{RUN}.t'+cyc+'z.ocn.bkgerr_stddev.nc')
#    config = plot_config(grid_file=grid_file,
#                         data_file=data_file,
#                         colormap=bmat_cmap,
#                         comout=os.path.join(comout, 'vrfy', 'bkgerr'))
#
#    #######################################
#    # zonal slices
#
#    for lat in np.arange(-60, 60, 10):
#
#        for max_depth in [700.0, 5000.0]:
#            config['lat'] = lat
#            config['max depth'] = max_depth
#
#            # Temperature
#            config.update({'variable': 'Temp', 'levels': [1], 'bounds': [0, 1.5]})
#            plot_zonal_slice(config)
#
#            # Salinity
#            config.update({'variable': 'Salt', 'levels': [1], 'bounds': [0, .2]})
#            plot_zonal_slice(config)
#
#    #######################################
#    # Horizontal slices
#
#    # Temperature
#    config.update({'variable': 'Temp', 'levels': [1], 'bounds': [0, 2]})
#    plot_horizontal_slice(config)
#
#    # Salinity
#    config.update({'variable': 'Salt', 'bounds': [0, 0.2]})
#    plot_horizontal_slice(config)
#
#    # Sea surface height
#    config.update({'variable': 'ave_ssh', 'bounds': [0, 0.1]})
#    plot_horizontal_slice(config)
#
class StatePlotter:

    def __init__(self, config_dict):
        self.config = config_dict
#        self.grid_file = config['grid file']
#        self.data_file = config['fields file']
#        self.variable = config['variable']
#        self.levels = config['levels'] 
#        self.bounds = config['bounds']
#        self.colormap = config['colormap']
#        self.lats = config['lats']
#        self.comout = config['comout']
#        self.maxdepth = 5000.0
#        self.proj = 'Global'
#     
        ...
        # Where config contains the bounds, filename and whatever else is needed to plot stuff

    def plot(self):
        # Loop over variables, slices (horiz and vertical) and projections ... and whatever else is needed
   
        #######################################
        # zonal slices

        for lat in self.config['lats']:
            self.config['lat'] = lat

            for max_depth in self.config['max depths']:
                self.config['max depth'] = max_depth

                for variable in self.config['zonal variables']:
                # Temperature
                    bounds = self.config['all bounds'][variable]
                    self.config.update({'variable': variable, 'bounds': bounds})
                    plot_zonal_slice(self.config)

                # Salinity
#                self.config.update({'variable': 'Salt', 'levels': [1], 'bounds': [0, .2]})
#                plot_zonal_slice(config)

        #######################################
        # Horizontal slices

        for variable in self.config['horiz variables']:
            bounds = self.config['all bounds'][variable]
            self.config.update({'variable': variable, 'bounds': bounds})
            plot_horizontal_slice(self.config)

#        # Temperature
#        self.config.update({'variable': 'Temp', 'levels': [1], 'bounds': [0, 2]})
#        plot_horizontal_slice(config)
#
#        # Salinity
#        self.config.update({'variable': 'Salt', 'bounds': [0, 0.2]})
#        plot_horizontal_slice(config)
#
#        # Sea surface height
#        self.config.update({'variable': 'ave_ssh', 'bounds': [0, 0.1]})
#        plot_horizontal_slice(config)


