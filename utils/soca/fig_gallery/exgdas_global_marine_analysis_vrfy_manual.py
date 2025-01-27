#!/usr/bin/env python3

import os
import numpy as np
import gen_eva_obs_yaml
import marine_eva_post
import diag_statistics
from multiprocessing import Process
from soca_vrfy import statePlotter, plotConfig
import subprocess

comout = os.getenv('COM_OCEAN_ANALYSIS')
com_ice_history = os.getenv('COM_ICE_HISTORY_PREV')
com_ocean_history = os.getenv('COM_OCEAN_HISTORY_PREV')
cyc = os.getenv('cyc')
bcyc = os.getenv('bcyc')
gcyc = os.getenv('gcyc')
RUN = os.getenv('RUN')

# Construct the first potential grid_file path
vrfy_grid_file = os.path.join(comout, f'{RUN}.t'+bcyc+'z.ocngrid.nc')

# Check if the file exists, then decide on grid_file
if os.path.exists(vrfy_grid_file):
    grid_file = vrfy_grid_file
else:
    grid_file = '/scratch1/NCEPDEV/da/common/validation/vrfy/gdas.t21z.ocngrid.nc'

layer_file = os.path.join(comout, f'{RUN}.t'+cyc+'z.ocninc.nc')

# for eva
diagdir = os.path.join(comout, 'diags')
HOMEgfs = os.getenv('HOMEgfs')

# Get flags from environment variables (set in the bash driver)
run_ensemble_analysis = os.getenv('RUN_ENSENBLE_ANALYSIS', 'OFF').upper() == 'ON'
run_bkgerr_analysis = os.getenv('RUN_BACKGROUND_ERROR_ANALYSIS', 'OFF').upper() == 'ON'
run_bkg_analysis = os.getenv('RUN_BACKGROUND_ANALYSIS', 'OFF').upper() == 'ON'
run_increment_analysis = os.getenv('RUN_INCREMENT_ANALYSIS', 'OFF').upper() == 'ON'
run_eva_analysis = os.getenv('RUN_EVA_ANALYSIS', 'OFF').upper() == 'ON'

# Initialize an empty list for the main config
configs = [plotConfig(grid_file=grid_file,
                      data_file=os.path.join(comout, f'{RUN}.t'+cyc+'z.ocnana.nc'),
                      variables_horiz={'ave_ssh': [-1.8, 1.3],
                                       'Temp': [-1.8, 34.0],
                                       'Salt': [32, 40]},
                      colormap='nipy_spectral',
                      comout=os.path.join(comout, 'vrfy', 'ana')),   # ocean surface analysis
           plotConfig(grid_file=grid_file,
                      data_file=os.path.join(comout, f'{RUN}.t'+cyc+'z.iceana.nc'),
                      variables_horiz={'aice_h': [0.0, 1.0],
                                       'hi_h': [0.0, 4.0],
                                       'hs_h': [0.0, 0.5]},
                      colormap='jet',
                      projs=['North', 'South', 'Global'],
                      comout=os.path.join(comout, 'vrfy', 'ana'))]   # sea ice analysis

# Define each config and add to main_config if its flag is True
if run_ensemble_analysis:
    config_ens = [plotConfig(grid_file=grid_file,
                             data_file=os.path.join(comout, f'{RUN}.t{cyc}z.ocn.recentering_error.nc'),
                             variables_horiz={'ave_ssh': [-1, 1]},
                             colormap='seismic',
                             comout=os.path.join(comout, 'vrfy', 'recentering_error')),   # recentering error
                  plotConfig(grid_file=grid_file,
                             data_file=os.path.join(comout, f'{RUN}.t{cyc}z.ocn.ssh_steric_stddev.nc'),
                             variables_horiz={'ave_ssh': [0, 0.8]},
                             colormap='gist_ncar',
                             comout=os.path.join(comout, 'vrfy', 'bkgerr', 'ssh_steric_stddev')),   # ssh steric stddev
                  plotConfig(grid_file=grid_file,
                             data_file=os.path.join(comout, f'{RUN}.t{cyc}z.ocn.ssh_unbal_stddev.nc'),
                             variables_horiz={'ave_ssh': [0, 0.8]},
                             colormap='gist_ncar',
                             comout=os.path.join(comout, 'vrfy', 'bkgerr', 'ssh_unbal_stddev')),   # ssh unbal stddev
                  plotConfig(grid_file=grid_file,
                             data_file=os.path.join(comout, f'{RUN}.t{cyc}z.ocn.ssh_total_stddev.nc'),
                             variables_horiz={'ave_ssh': [0, 0.8]},
                             colormap='gist_ncar',
                             comout=os.path.join(comout, 'vrfy', 'bkgerr', 'ssh_total_stddev')),   # ssh total stddev
                  plotConfig(grid_file=grid_file,
                             data_file=os.path.join(comout, f'{RUN}.t{cyc}z.ocn.steric_explained_variance.nc'),
                             variables_horiz={'ave_ssh': [0, 1]},
                             colormap='seismic',
                             comout=os.path.join(comout, 'vrfy', 'bkgerr', 'steric_explained_variance'))]   # steric explained variance
    configs.extend(config_ens)

if run_bkgerr_analysis:
    config_bkgerr = [plotConfig(grid_file=grid_file,
                                data_file=os.path.join(comout, os.path.pardir, os.path.pardir,
                                                      'bmatrix', 'ice', f'{RUN}.t'+cyc+'z.ice.bkgerr_stddev.nc'),
                                variables_horiz={'aice_h': [0.0, 0.5],
                                                 'hi_h': [0.0, 2.0],
                                                 'hs_h': [0.0, 0.2]},
                                colormap='jet',
                                projs=['North', 'South', 'Global'],
                                comout=os.path.join(comout, 'vrfy', 'bkgerr')),   # sea ice baigerr stddev
                     plotConfig(grid_file=grid_file,
                                layer_file=layer_file,
                                data_file=os.path.join(comout, os.path.pardir, os.path.pardir,
                                                      'bmatrix', 'ocean', f'{RUN}.t'+cyc+'z.ocean.bkgerr_stddev.nc'),
                                lats=np.arange(-60, 60, 10),
                                lons=np.arange(-280, 80, 30),
                                variables_zonal={'Temp': [0, 2],
                                                 'Salt': [0, 0.2],
                                                 'u': [0, 0.5],
                                                 'v': [0, 0.5]},
                                variables_meridional={'Temp': [0, 2],
                                                      'Salt': [0, 0.2],
                                                      'u': [0, 0.5],
                                                      'v': [0, 0.5]},
                                variables_horiz={'Temp': [0, 2],
                                                 'Salt': [0, 0.2],
                                                 'u': [0, 0.5],
                                                 'v': [0, 0.5],
                                                 'ave_ssh': [0, 0.1]},
                                colormap='jet',
                                comout=os.path.join(comout, 'vrfy', 'bkgerr'))]   # ocn bkgerr stddev
    configs.extend(config_bkgerr)

if run_bkg_analysis:
    config_bkg = [plotConfig(grid_file=grid_file,
                             data_file=os.path.join(com_ice_history, f'{RUN}.ice.t{gcyc}z.inst.f006.nc'),
                             variables_horiz={'aice_h': [0.0, 1.0],
                                              'hi_h': [0.0, 4.0],
                                              'hs_h': [0.0, 0.5]},
                             colormap='jet',
                             projs=['North', 'South', 'Global'],
                             comout=os.path.join(comout, 'vrfy', 'bkg')),   # sea ice background
                  plotConfig(grid_file=grid_file,
                             layer_file=layer_file,
                             data_file=os.path.join(com_ocean_history, f'{RUN}.ocean.t{gcyc}z.inst.f006.nc'),
                             lats=np.arange(-60, 60, 10),
                             lons=np.arange(-280, 80, 30),
                             variables_zonal={'Temp': [-1.8, 34.0],
                                              'Salt': [32, 40],
                                              'u': [-1.0, 1.0],
                                              'v': [-1.0, 1.0]},
                             variables_meridional={'Temp': [-1.8, 34.0],
                                                   'Salt': [32, 40],
                                                   'u': [-1.0, 1.0],
                                                   'v': [-1.0, 1.0]},
                             variables_horiz={'ave_ssh': [-1.8, 1.3],
                                              'Temp': [-1.8, 34.0],
                                              'Salt': [32, 40],
                                              'u': [-1.0, 1.0],
                                              'v': [-1.0, 1.0]},
                             colormap='nipy_spectral',
                             comout=os.path.join(comout, 'vrfy', 'bkg'))]
    configs.extend(config_bkg)

if run_increment_analysis:
    config_incr = [plotConfig(grid_file=grid_file,
                              layer_file=layer_file,
                              data_file=os.path.join(comout, f'{RUN}.t'+cyc+'z.ocninc.nc'),
                              lats=np.arange(-60, 60, 10),
                              lons=np.arange(-280, 80, 30),
                              variables_zonal={'Temp': [-0.5, 0.5],
                                               'Salt': [-0.1, 0.1]},
                              variables_horiz={'Temp': [-0.5, 0.5],
                                               'Salt': [-0.1, 0.1],
                                               'ave_ssh': [-0.1, 0.1]},
                              variables_meridional={'Temp': [-0.5, 0.5],
                                                    'Salt': [-0.1, 0.1]},
                              colormap='seismic',
                              comout=os.path.join(comout, 'vrfy', 'incr')),   # ocean increment
                   plotConfig(grid_file=grid_file,
                              data_file=os.path.join(comout, f'{RUN}.t'+cyc+'z.ice.incr.nc'),
                              lats=np.arange(-60, 60, 10),
                              variables_horiz={'aice_h': [-0.2, 0.2],
                                               'hi_h': [-0.5, 0.5],
                                               'hs_h': [-0.1, 0.1]},
                              colormap='seismic',
                              projs=['North', 'South'],
                              comout=os.path.join(comout, 'vrfy', 'incr')),   # sea ice increment
                   plotConfig(grid_file=grid_file,
                              data_file=os.path.join(comout, f'{RUN}.t'+cyc+'z.ice.incr.postproc.nc'),
                              lats=np.arange(-60, 60, 10),
                              variables_horiz={'aice_h': [-0.2, 0.2],
                                               'hi_h': [-0.5, 0.5],
                                               'hs_h': [-0.1, 0.1]},
                              colormap='seismic',
                              projs=['North', 'South'],
                              comout=os.path.join(comout, 'vrfy', 'incr.postproc'))]   # sea ice increment after postprocessing
    configs.extend(config_incr)


# plot marine analysis vrfy

def plot_marine_vrfy(config):
    ocnvrfyPlotter = statePlotter(config)
    ocnvrfyPlotter.plot()


# Number of processes
num_processes = len(configs)

# Create a list to store the processes
processes = []

# Iterate over configs
for config in configs[:num_processes]:
    process = Process(target=plot_marine_vrfy, args=(config,))
    process.start()
    processes.append(process)

# Wait for all processes to finish
for process in processes:
    process.join()

#######################################
# eva plots
#######################################
if run_eva_analysis:
    evadir = os.path.join(HOMEgfs, 'sorc', f'{RUN}.cd', 'ush', 'eva')
    marinetemplate = os.path.join(evadir, 'marine_gdas_plots.yaml')
    varyaml = os.path.join(comout, 'yaml', 'var.yaml')

    # it would be better to refrence the dirs explicitly with the comout path
    # but eva doesn't allow for specifying output directories
    os.chdir(os.path.join(comout, 'vrfy'))
    if not os.path.exists('preevayamls'):
        os.makedirs('preevayamls')
    if not os.path.exists('evayamls'):
        os.makedirs('evayamls')

    gen_eva_obs_yaml.gen_eva_obs_yaml(varyaml, marinetemplate, 'preevayamls')

    files = os.listdir('preevayamls')
    for file in files:
        infile = os.path.join('preevayamls', file)
        marine_eva_post.marine_eva_post(infile, 'evayamls', diagdir)

    files = os.listdir('evayamls')
    for file in files:
        infile = os.path.join('evayamls', file)
        print('running eva on', infile)
        subprocess.run(['eva', infile], check=True)
else:
    print("RUN_EVA_PLOT is set to OFF. Skipping EVA plot generation.")
#######################################
# calculate diag statistics
#######################################

# As of 11/12/2024 not working
# diag_statistics.get_diag_stats()
