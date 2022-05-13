#!/usr/bin/env python3
################################################################################
#  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exufsda_global_marine_analysis_prep.py
# Script description:  Stages files and generates YAML for UFS Global Marine Analysis
#
# Author: Guillaume Vernieres      Org: NCEP/EMC     Date: 2022-03-28
#
# Abstract: This script stages the marine observations necessary
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

# Setup the archive, local and shared R2D2 databases
ufsda.r2d2.setup(r2d2_config_yaml='r2d2_config.yaml', shared_root=COMIN_OBS)

# create config dict from runtime env
stage_cfg = ufsda.parse_config(templateyaml=os.path.join(os.getenv('HOMEgfs'),
                                                         'parm',
                                                         'templates',
                                                         'stage.yaml'), clean=True)

# stage observations from R2D2 to COMIN_OBS and then link to analysis subdir
ufsda.stage.obs(stage_cfg)
