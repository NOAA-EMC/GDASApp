#!/usr/bin/env python3
################################################################################
#  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exufsda_global_marine_analysis_prep.py
# Script description:  Stages files and generates YAML for UFS Global Marine Analysis
#
# Author: Guillaume Vernieres      Org: NCEP/EMC     Date: 2022-03-28
#
# Abstract: This script stages the marine observations necessar
#           to produce a UFS Global Marine Analysis.
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
# TODO: ufsda should be installed
sys.path.append(os.path.join(os.getenv('HOMEgfs'), 'ush'))

# import UFSDA utilities
import ufsda

# get runtime environment variables
COMOUT = os.getenv('COMOUT')
COMIN_OBS = os.getenv('COMIN_OBS')

# create analysis directory for files
anl_dir = os.path.join(COMOUT, 'analysis')
ufsda.mkdir(anl_dir)

# Set the R2D2_CONFIG environement variable
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
stage_cfg = ufsda.parse_config(templateyaml=os.path.join(os.getenv('HOMEgfs'),
                                                         'parm',
                                                         'templates',
                                                         'stage.yaml'), clean=True)

# stage observations from R2D2 to COMIN_OBS and then link to analysis subdir
ufsda.stage.obs(stage_cfg)
