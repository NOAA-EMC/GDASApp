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
from datetime import datetime, timedelta
from wxflow import FileHandler, Logger

logger = Logger()


# TODO: Move this somewhere else?
def list_all_files(dir_in, dir_out, wc='*', fh_list=[]):
    files = glob.glob(os.path.join(dir_in, wc))
    for file_src in files:
        file_dst = os.path.join(dir_out, os.path.basename(file_src))
        fh_list.append([file_src, file_dst])
    return fh_list


logger.info(f"---------------- Copy from RUNDIR to COMOUT")

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
mdate = datetime.strftime(datetime.strptime(cdate, '%Y%m%d%H'), '%Y-%m-%dT%H:00:00Z')

post_file_list = []

# Make a copy the IAU increment
post_file_list.append([os.path.join(anl_dir, 'inc.nc'),
                       os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.ocninc.nc')])

domains = ['ocn', 'ice']
for domain in domains:
    # Copy of the diagonal of the background error for the cycle
    post_file_list.append([os.path.join(anl_dir, f'{domain}.bkgerr_stddev.incr.{mdate}.nc'),
                           os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.{domain}.bkgerr_stddev.nc')])

    # Copy the recentering error
    #post_file_list.append([os.path.join(anl_dir, 'static_ens', f'{domain}.ssh_recentering_error.incr.{bdate}.nc'),
    #                       os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.{domain}.recentering_error.nc')])

    # Copy the ice and ocean increments
    post_file_list.append([os.path.join(anl_dir, 'Data', f'{domain}.3dvarfgat_pseudo.incr.{mdate}.nc'),
                           os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.{domain}.incr.nc')])

    # Copy the analysis at the start of the window
    post_file_list.append([os.path.join(anl_dir, 'Data', f'{domain}.3dvarfgat_pseudo.an.{mdate}.nc'),
                           os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.{domain}ana.nc')])

# Copy of the ssh diagnostics
#for string in ['ssh_steric_stddev', 'ssh_unbal_stddev', 'ssh_total_stddev', 'steric_explained_variance']:
#    post_file_list.append([os.path.join(anl_dir, 'static_ens', f'ocn.{string}.incr.{bdate}.nc'),
#                           os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.ocn.{string}.nc')])

# Copy DA grid (computed for the start of the window)
post_file_list.append([os.path.join(anl_dir, 'soca_gridspec.nc'),
                       os.path.join(com_ocean_analysis, f'{RUN}.t{bcyc}z.ocngrid.nc')])

# Copy the CICE analysis restart
cdateice = pdy + '.' + cyc + '0000'
post_file_list.append([os.path.join(anl_dir, 'Data', f'{cdateice}.cice_model.res.nc'),
                       os.path.join(com_ice_restart, f'{cdate}.cice_model_anl.res.nc')])

FileHandler({'copy': post_file_list}).sync()

# create COM sub-directories
FileHandler({'mkdir': [os.path.join(com_ocean_analysis, 'diags'),
                       os.path.join(com_ocean_analysis, 'bump'),
                       os.path.join(com_ocean_analysis, 'yaml')]}).sync()

# ioda output files
fh_list = list_all_files(os.path.join(anl_dir, 'diags'),
                         os.path.join(com_ocean_analysis, 'diags'))

# yaml configurations
fh_list = list_all_files(os.path.join(anl_dir),
                         os.path.join(com_ocean_analysis, 'yaml'), wc='*.yaml', fh_list=fh_list)

FileHandler({'copy': fh_list}).sync()
