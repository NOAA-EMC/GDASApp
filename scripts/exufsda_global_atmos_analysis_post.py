#!/usr/bin/env python3
################################################################################
####  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exufsda_global_atmos_analysis_post.py
# Script description:  Combines IODA output and archives to R2D2
#
# Author: Cory Martin      Org: NCEP/EMC     Date: 2021-12-29
#
# Abstract: This script combines IODA formatted output diagnostic files
#           from separate PEs into one file per 'ObsSpace' and then
#           archives each concatenated file into the R2D2 local user database.
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

# create config dict from runtime env
yaml_template = os.getenv('ATMANALPOSTYAML',
                          os.path.join(ufsda_home,
                                       'parm',
                                       'templates',
                                       'post.yaml'))
post_cfg = ufsda.parse_config(templateyaml=yaml_template, clean=True)

# merge IODA files
ufsda.post.merge_diags(post_cfg)

# archive with R2D2
ufsda.post.archive_diags(post_cfg)

# clean up
ufsda.post.cleanup(post_cfg)
