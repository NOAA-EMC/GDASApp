#!/usr/bin/env python3
################################################################################
#  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exufsda_global_marine_analysis_vrfy.py
# Script description:  State and observation space verification for the
#                      UFS Global Marine Analysis
#
# Author: Guillaume Vernieres      Org: NCEP/EMC     Date: 2023-01-23
#
# Abstract: This script produces figures relevant to the marine DA cycle
#
# $Id$
#
# Attributes:
#   Language: Python3
#
################################################################################

import os
import numpy as np
import gen_eva_obs_yaml
import marine_eva_post
import diag_statistics
from multiprocessing import Process
from soca_vrfy import statePlotter, plotConfig
import subprocess

comout = os.path.realpath(os.getenv('COM_OCEAN_ANALYSIS'))
com_ice_history = os.path.realpath(os.getenv('COM_ICE_HISTORY_PREV'))
com_ocean_history = os.path.realpath(os.getenv('COM_OCEAN_HISTORY_PREV'))
cyc = os.getenv('cyc')
RUN = os.getenv('RUN')

bcyc = str((int(cyc) - 3) % 24).zfill(2)
gcyc = str((int(cyc) - 6) % 24).zfill(2)
grid_file = os.path.join(comout, f'{RUN}.t'+bcyc+'z.ocngrid.nc')
layer_file = os.path.join(comout, f'{RUN}.t'+cyc+'z.ocninc.nc')

# for eva
diagdir = os.path.join(comout, 'diags')
HOMEgfs = os.getenv('HOMEgfs')


# plot marine analysis vrfy

def plot_marine_vrfy(config):
    ocnvrfyPlotter = statePlotter(config)
    ocnvrfyPlotter.plot()

# Define configurations dynamically


configs = [plotConfig(grid_file=grid_file,
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
                      comout=os.path.join(comout, 'vrfy', 'bkgerr', 'steric_explained_variance')),   # steric explained variance
           plotConfig(grid_file=grid_file,
                      layer_file=layer_file,
                      data_file=os.path.join(comout, f'{RUN}.t'+cyc+'z.ocn.bkgerr_stddev.nc'),
                      lats=np.arange(-60, 60, 10),
                      lons=np.arange(-280, 80, 30),
                      variables_zonal={'Temp': [0, 2],
                                       'Salt': [0, 0.2],
                                       'u': [0, 0.2],
                                       'v': [0, 0.2]},
                      variables_meridional={'Temp': [0, 2],
                                            'Salt': [0, 0.2],
                                            'u': [0, 0.2],
                                            'v': [0, 0.2]},
                      variables_horiz={'Temp': [0, 2],
                                       'Salt': [0, 0.2],
                                       'u': [0, 0.2],
                                       'v': [0, 0.2],
                                       'ave_ssh': [0, 0.1]},
                      colormap='jet',
                      comout=os.path.join(comout, 'vrfy', 'bkgerr')),   # ocn bkgerr stddev
           plotConfig(grid_file=grid_file,
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
                      colormap='RdBu',
                      comout=os.path.join(comout, 'vrfy', 'incr')),   # ocean increment
           plotConfig(grid_file=grid_file,
                      data_file=os.path.join(comout, f'{RUN}.t'+cyc+'z.ice.incr.nc'),
                      lats=np.arange(-60, 60, 10),
                      variables_horiz={'aicen': [-0.2, 0.2],
                                       'hicen': [-0.5, 0.5],
                                       'hsnon': [-0.1, 0.1]},
                      colormap='RdBu',
                      projs=['North', 'South'],
                      comout=os.path.join(comout, 'vrfy', 'incr')),   # sea ice increment
           plotConfig(grid_file=grid_file,
                      data_file=os.path.join(comout, f'{RUN}.t'+cyc+'z.iceana.nc'),
                      variables_horiz={'aicen': [0.0, 1.0],
                                       'hicen': [0.0, 4.0],
                                       'hsnon': [0.0, 0.5]},
                      colormap='jet',
                      projs=['North', 'South', 'Global'],
                      comout=os.path.join(comout, 'vrfy', 'ana')),   # sea ice analysis
           plotConfig(grid_file=grid_file,
                      data_file=os.path.join(com_ice_history, f'{RUN}.ice.t{gcyc}z.inst.f006.nc'),
                      variables_horiz={'aice_h': [0.0, 1.0],
                                       'hs_h': [0.0, 4.0],
                                       'hi_h': [0.0, 0.5]},
                      colormap='jet',
                      projs=['North', 'South', 'Global'],
                      comout=os.path.join(comout, 'vrfy', 'bkg')),   # sea ice background
           plotConfig(grid_file=grid_file,
                      data_file=os.path.join(comout, f'{RUN}.t'+cyc+'z.ocnana.nc'),
                      variables_horiz={'ave_ssh': [-1.8, 1.3],
                                       'Temp': [-1.8, 34.0],
                                       'Salt': [30, 38]},
                      colormap='nipy_spectral',
                      comout=os.path.join(comout, 'vrfy', 'ana')),   # ocean surface analysis
           plotConfig(grid_file=grid_file,
                      layer_file=layer_file,
                      data_file=os.path.join(com_ocean_history, f'{RUN}.ocean.t{gcyc}z.inst.f006.nc'),
                      lats=np.arange(-60, 60, 10),
                      lons=np.arange(-280, 80, 30),
                      variables_zonal={'Temp': [-1.8, 34.0],
                                       'Salt': [30, 38]},
                      variables_meridional={'Temp': [-1.8, 34.0],
                                            'Salt': [30, 38]},
                      variables_horiz={'ave_ssh': [-1.8, 1.3],
                                       'Temp': [-1.8, 34.0],
                                       'Salt': [30, 38]},
                      colormap='nipy_spectral',
                      comout=os.path.join(comout, 'vrfy', 'bkg'))]   # ocean surface background

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

evadir = os.path.join(HOMEgfs, 'sorc', f'{RUN}.cd', 'ush', 'eva')
marinetemplate = os.path.join(evadir, 'marine_gdas_plots.yaml')
varyaml = os.path.join(comout, 'yaml', 'var_original.yaml')

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

#######################################
# calculate diag statistics
#######################################

diag_statistics.get_diag_stats()
