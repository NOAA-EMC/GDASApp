#!/usr/bin/env python3
################################################################################
####  UNIX Script Documentation Block
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

# get absolute path of ush/ directory either from env or relative to this file
my_dir = os.path.dirname(__file__)
my_home = os.path.dirname(os.path.dirname(my_dir))
ufsda_home = os.path.join(os.environ['HOMEgfs'], 'sorc', 'ufs_da.fd', 'UFS-DA')
sys.path.append(os.path.join(os.getenv('HOMEgfs', my_home), 'ush'))
print(f"sys.path={sys.path}")

# import UFSDA utilities
import ufsda

# get COMOUT from env
COMOUT = os.getenv('COMOUT', './')

# create analysis directory for files
anl_dir = os.path.join(COMOUT, 'analysis')
ufsda.mkdir(anl_dir)

# create config dict from runtime env
yaml_template = os.getenv('ATMANALPREPYAML',
                          os.path.join(ufsda_home,
                                       'parm',
                                       'templates',
                                       'stage.yaml'))
stage_cfg = ufsda.parse_config(templateyaml=yaml_template, clean=True)

# stage observations from R2D2 to COMIN_OBS and then link to analysis subdir
ufsda.stage.obs(stage_cfg)

# stage backgrounds from COMIN_GES to analysis subdir
ufsda.stage.background(stage_cfg)

# stage background error parameters files
ufsda.stage.berror(stage_cfg)

# stage additional needed files
ufsda.stage.fv3jedi(stage_cfg)

# generate YAML file for fv3jedi_var
var_yaml = os.path.join(anl_dir, 'fv3jedi_var.yaml')
yaml_template = os.getenv('ATMANALYAML',
                          os.path.join(ufsda_home,
                                       'parm',
                                       'templates',
                                       'ufsda_global_atm_3dvar.yaml'))
ufsda.gen_yaml(var_yaml, yaml_template)
