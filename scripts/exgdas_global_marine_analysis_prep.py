#!/usr/bin/env python3
################################################################################
#  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exufsda_global_atmos_analysis_prep.py
# Script description:  Stages files and generates YAML for UFS Global Atmosphere Analysis
#
# Author: Cory Martin      Org: NCEP/EMC     Date: 2021-12-21
#
# Abstract: This script stages necessary input files and produces YAML
#           configuration input file for FV3-JEDI executable(s) needed
#           to produce a UFS Global Atmospheric Analysis.
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

# get absolute path of ush/ directory either from env or relative to this file
sys.path.append('/home/gvernier/sandboxes/GDASApp/ush')
print(f"sys.path={sys.path}")

# import UFSDA utilities
import ufsda

# get runtime environment variables
COMOUT = os.getenv('COMOUT')
COMIN_OBS = os.getenv('COMIN_OBS')

# create analysis directory for files
anl_dir = os.path.join(COMOUT, 'analysis')
ufsda.mkdir(anl_dir)

# Set the R2D2_CONFIG environement variable
#
# TODO: Generate this yaml with ufsda.parse_config ... or something?
r2d2_config = {'databases': {'archive': {'bucket': 'archive.jcsda',
                                         'cache_fetch': True,
                                         'class': 'S3DB'},
                             'local': {'cache_fetch': False,
                                       'class': 'LocalDB',
                                       'root': './r2d2-local/'},
                             'shared': {'cache_fetch': False,
                                        'class': 'LocalDB',
                                        'root': COMIN_OBS}},
               'fetch_order': ['shared'],
               'store_order': ['local']}

f = open('r2d2_config.yaml', 'w')
yaml.dump(r2d2_config, f, sort_keys=False, default_flow_style=False)
os.environ['R2D2_CONFIG'] = 'r2d2_config.yaml'

# create config dict from runtime env
# TODO: Generate this yaml with ufsda.parse_config
# TODO: "window length" below is for the obs database, no the DA window
stage_cfg = {'COMOUT': COMOUT,
             'r2d2_obs_db': 'shared',
             'r2d2_obs_dump': 'soca',
             'r2d2_obs_src': 'gdasapp',
             'window begin': '20180415',
             'window length': '24'}
stage_cfg['observations'] = [{'obs space': {'name': 'adt_j3',
                                            'obsdatain': {'obsfile': './obs'}}},
                             {'obs space': {'name': 'sst_noaa19_l3u',
                                            'obsdatain': {'obsfile': './obs'}}}]

test = stage_cfg['observations'][0]['obs space']['obsdatain']

# stage observations from R2D2 to COMIN_OBS and then link to analysis subdir
ufsda.stage.obs(stage_cfg)
