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
from soca_vrfy import plot_increment, plot_analysis
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
# INCREMENT
#######################################

plot_increment(comout, cyc, RUN, grid_file)

#######################################
# Analysis/Background
#######################################

plot_analysis(comout, 
              com_ice_history, 
              com_ocean_history, 
              cyc, 
              RUN, 
              grid_file, 
              gcyc)

#######################################
# eva plots

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

diag_statistics.get_diag_stats()
