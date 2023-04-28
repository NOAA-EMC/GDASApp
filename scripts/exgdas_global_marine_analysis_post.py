#!/usr/bin/env python3
################################################################################
#  UNIX Script Documentation Block
#                      .                                             .
# Script name:         exufsda_global_marine_analysis_post.py
# Script description:  Copies files from rundir to comrot after analysis run
#
# Author: Andrew Eichmann    Org: NCEP/EMC     Date: 2023-04-24
#
# Abstract: This script, to be called from jobs/JGDAS_GLOBAL_OCEAN_ANALYSIS_POST
#           in global-workflow, copies ocean da files from the rundir to the comrot
#
# $Id$
#
# Attributes:
#   Language: Python3
#
################################################################################

# import os and sys to add ush to path
import os
import glob
import shutil
import logging
from datetime import datetime, timedelta
import ufsda

# set up logger
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
logging.info(f"---------------- Copy from RUNDIR to COMOUT")

com_ocean_analysis = os.getenv('COM_OCEAN_ANALYSIS')
com_ice_restart = os.getenv('COM_ICE_RESTART')
anl_dir = os.getenv('DATA')
cdate = os.getenv('CDATE')
pdy = os.getenv('PDY')
staticsoca_dir = os.getenv('SOCA_INPUT_FIX_DIR')
RUN = os.getenv('CDUMP')
cyc = str(os.getenv('cyc')).zfill(2)
bcyc = str((int(cyc) - 3) % 24).zfill(2)
gcyc = str((int(cyc) - 6) % 24).zfill(2)  # previous cycle
bdatedt = datetime.strptime(cdate, '%Y%m%d%H') - timedelta(hours=3)
bdate = datetime.strftime(bdatedt, '%Y-%m-%dT%H:00:00Z')

# Make a copy the IAU increment
ufsda.disk_utils.copyfile(os.path.join(anl_dir, 'inc.nc'),
                          os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.ocninc.nc'))

# Copy of the ioda output files, as is for now
ufsda.disk_utils.copytree(os.path.join(anl_dir, 'diags'),
                          os.path.join(com_ocean_analysis, 'diags'))

# Copy of the diagonal of the background error for the cycle
ufsda.disk_utils.copyfile(os.path.join(anl_dir, f'ocn.bkgerr_stddev.incr.{bdate}.nc'),
                          os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.ocn.bkgerr_stddev.nc'))
ufsda.disk_utils.copyfile(os.path.join(anl_dir, f'ice.bkgerr_stddev.incr.{bdate}.nc'),
                          os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.ice.bkgerr_stddev.nc'))

# Copy the ice and ocean increments
ufsda.disk_utils.copyfile(os.path.join(anl_dir, 'Data', f'ocn.3dvarfgat_pseudo.incr.{bdate}.nc'),
                          os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.ocn.incr.nc'))
ufsda.disk_utils.copyfile(os.path.join(anl_dir, 'Data', f'ice.3dvarfgat_pseudo.incr.{bdate}.nc'),
                          os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.ice.incr.nc'))

# Copy the localization and correlation operators
ufsda.disk_utils.copytree(os.path.join(anl_dir, 'bump'),
                          os.path.join(com_ocean_analysis, 'bump'))

# Copy DA grid (computed for the start of the window)
ufsda.disk_utils.copyfile(os.path.join(anl_dir, 'soca_gridspec.nc'),
                          os.path.join(com_ocean_analysis, f'{RUN}.t{bcyc}z.ocngrid.nc'))

# Copy the analysis at the start of the window
ufsda.disk_utils.copyfile(os.path.join(anl_dir, 'Data', f'ocn.3dvarfgat_pseudo.an.{bdate}.nc'),
                          os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.ocnana.nc'))
ufsda.disk_utils.copyfile(os.path.join(anl_dir, 'Data', f'ice.3dvarfgat_pseudo.an.{bdate}.nc'),
                          os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.iceana.nc'))

# Copy the CICE analysis restart
cdateice = pdy + '.' + cyc + '0000'
ufsda.disk_utils.copyfile(os.path.join(anl_dir, 'Data', f'{cdateice}.cice_model.res.nc'),
                          os.path.join(com_ice_restart, f'{cdate}.cice_model_anl.res.nc'))

# Copy logs
ufsda.mkdir(os.path.join(com_ocean_analysis, 'logs'))
for file in glob.glob(os.path.join(anl_dir, '*.out')):
    ufsda.disk_utils.copyfile(file, os.path.join(com_ocean_analysis, 'logs'))

# Copy var.yaml
ufsda.mkdir(os.path.join(com_ocean_analysis, 'yaml'))
for file in glob.glob(os.path.join(anl_dir, '*.yaml')):
    ufsda.disk_utils.copyfile(file, os.path.join(com_ocean_analysis, 'yaml'))
