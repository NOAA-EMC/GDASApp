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
from soca_vrfy import statePlotter, plotConfig
import subprocess
from datetime import datetime, timedelta

comout = os.getenv('COM_OCEAN_ANALYSIS')
com_ice_history = os.getenv('COM_ICE_HISTORY_PREV')
com_ocean_history = os.getenv('COM_OCEAN_HISTORY_PREV')
cyc = os.getenv('cyc')
RUN = os.getenv('RUN')
gcyc = str((int(cyc) - 6) % 24).zfill(2)

bcyc = str((int(cyc) - 3) % 24).zfill(2)
grid_file = os.path.join(comout, f'{RUN}.t'+bcyc+'z.ocngrid.nc')

# for eva
diagdir = os.path.join(comout, 'diags')
HOMEgfs = os.getenv('HOMEgfs')

#######################################
# ocean increment
#######################################

data_file = os.path.join(comout, f'{RUN}.t'+cyc+'z.ocninc.nc')
config = plotConfig(grid_file=grid_file,
                     data_file=data_file,
                     lats=np.arange(-60, 60, 10),
                     variables_zonal=['Temp', 'Salt'],
                     variables_horiz=['Temp', 'Salt', 'ave_ssh'],
                     allbounds={'Temp': [-0.5, 0.5],
                                'Salt': [-0.1, 0.1],
                                'ave_ssh': [-0.1, 0.1]},
                     colormap='RdBu',
                     comout=os.path.join(comout, 'vrfy', 'incr'))
ocnIncPlotter = statePlotter(config)
ocnIncPlotter.plot()

#######################################
# sea ice increment
#######################################

data_file = os.path.join(comout, f'{RUN}.t'+cyc+'z.ice.incr.nc')
config = plotConfig(grid_file=grid_file,
                     data_file=data_file,
                     lats=np.arange(-60, 60, 10),
                     variables_horiz=['aicen', 'hicen', 'hsnon'],
                     allbounds={'aicen': [-0.2, 0.2],
                                'hicen': [-0.5, 0.5],
                                'hsnon': [-0.1, 0.1]},
                     colormap='RdBu',
                     projs=['North', 'South'],
                     comout=os.path.join(comout, 'vrfy', 'incr'))
iceIncPlotter = statePlotter(config)
iceIncPlotter.plot()

#######################################
# sea ice analysis
#######################################

data_file = os.path.join(comout, f'{RUN}.t'+cyc+'z.iceana.nc')
config = plotConfig(grid_file=grid_file,
                     data_file=data_file,
                     variables_horiz=['aicen', 'hicen', 'hsnon'],
                     allbounds={'aicen': [0.0, 1.0],
                                'hicen': [0.0, 4.0],
                                'hsnon': [0.0, 0.5]},
                     colormap='jet',
                     projs=['North', 'South', 'Global'],
                     comout=os.path.join(comout, 'vrfy', 'ana'))
iceAnaPlotter = statePlotter(config)
iceAnaPlotter.plot()

#######################################
# sea ice background
#######################################

data_file = os.path.join(com_ice_history, f'{RUN}.t{gcyc}z.icef006.nc')
config = plotConfig(grid_file=grid_file,
                     data_file=data_file,
                     variables_horiz=['aice_h', 'hs_h', 'hi_h'],
                     allbounds={'aice_h': [0.0, 1.0],
                                'hs_h': [0.0, 4.0],
                                'hi_h': [0.0, 0.5]},
                     colormap='jet',
                     projs=['North', 'South', 'Global'],
                     comout=os.path.join(comout, 'vrfy', 'bkg'))
iceBkgPlotter = statePlotter(config)
iceBkgPlotter.plot()

#######################################
# ocean surface analysis
#######################################

data_file = os.path.join(comout, f'{RUN}.t'+cyc+'z.ocnana.nc')
config = plotConfig(grid_file=grid_file,
                     data_file=data_file,
                     variables_horiz=['ave_ssh', 'Temp', 'Salt'],
                     allbounds={'ave_ssh': [-1.8, 1.3],
                                'Temp': [-1.8, 34.0],
                                'Salt': [30, 38]},
                     colormap='jet',
                     comout=os.path.join(comout, 'vrfy', 'ana'))
ocnAnaPlotter = statePlotter(config)
ocnAnaPlotter.plot()

#######################################
# ocean surface background
#######################################

data_file = os.path.join(com_ocean_history, f'{RUN}.t{gcyc}z.ocnf006.nc')
config = plotConfig(grid_file=grid_file,
                     data_file=data_file,
                     variables_horiz=['ave_ssh', 'Temp', 'Salt'],
                     allbounds={'ave_ssh': [-1.8, 1.3],
                                'Temp': [-1.8, 34.0],
                                'Salt': [30, 38]},
                     colormap='jet',
                     comout=os.path.join(comout, 'vrfy', 'bkg'))
ocnBkgPlotter = statePlotter(config)
ocnBkgPlotter.plot()

#######################################
# background error
#######################################

data_file = os.path.join(comout, f'{RUN}.t'+cyc+'z.ocn.bkgerr_stddev.nc')
config = plotConfig(grid_file=grid_file,
                     data_file=data_file,
                     lats=np.arange(-60, 60, 10),
                     variables_zonal=['Temp', 'Salt'],
                     variables_horiz=['Temp', 'Salt', 'ave_ssh'],
                     allbounds={'Temp': [0, 2],
                                'Salt': [0, 0.2],
                                'ave_ssh': [0, 0.1]},
                     colormap='jet',
                     comout=os.path.join(comout, 'vrfy', 'bkgerr'))
bkgErrPlotter = statePlotter(config)
bkgErrPlotter.plot()

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
