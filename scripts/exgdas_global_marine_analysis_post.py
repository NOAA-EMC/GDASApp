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
from wxflow import AttrDict, FileHandler, Logger, parse_j2yaml
from multiprocessing import Process
import subprocess
import netCDF4
import re

logger = Logger()


# TODO: Move this somewhere else?
def list_all_files(dir_in, dir_out, wc='*', fh_list=[]):
    files = glob.glob(os.path.join(dir_in, wc))
    for file_src in files:
        file_dst = os.path.join(dir_out, os.path.basename(file_src))
        fh_list.append([file_src, file_dst])
    return fh_list


com_ocean_analysis = os.getenv('COM_OCEAN_ANALYSIS')
com_ice_analysis = os.getenv('COM_ICE_ANALYSIS')
com_ice_restart = os.getenv('COM_ICE_RESTART')
anl_dir = os.getenv('DATA')
cdate = os.getenv('CDATE')
pdy = os.getenv('PDY')
staticsoca_dir = os.getenv('SOCA_INPUT_FIX_DIR')
RUN = os.getenv('CDUMP')
cyc = str(os.getenv('cyc')).zfill(2)
bcyc = str((int(cyc) - 3) % 24).zfill(2)
gcyc = str((int(cyc) - 6) % 24).zfill(2)  # previous cycle
cdatedt = datetime.strptime(cdate, '%Y%m%d%H')
bdatedt = datetime.strptime(cdate, '%Y%m%d%H') - timedelta(hours=3)
bdate = datetime.strftime(bdatedt, '%Y-%m-%dT%H:00:00Z')
mdate = datetime.strftime(datetime.strptime(cdate, '%Y%m%d%H'), '%Y-%m-%dT%H:00:00Z')
nmem_ens = int(os.getenv('NMEM_ENS'))

logger.info(f"---------------- Copy from RUNDIR to COMOUT")

post_file_list = []

# Make a copy the IAU increment
post_file_list.append([os.path.join(anl_dir, 'inc.nc'),
                       os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.ocninc.nc')])

domains = ['ocn', 'ice']
for domain in domains:
    '''
    # Copy of the diagonal of the background error for the cycle
    post_file_list.append([os.path.join(anl_dir, f'{domain}.bkgerr_stddev.incr.{mdate}.nc'),
                           os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.{domain}.bkgerr_stddev.nc')])

    # Copy the recentering error
    if nmem_ens > 2:
        post_file_list.append([os.path.join(anl_dir, 'static_ens', f'{domain}.ssh_recentering_error.incr.{bdate}.nc'),
                               os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.{domain}.recentering_error.nc')])
    '''

    # Copy the ice and ocean increments
    post_file_list.append([os.path.join(anl_dir, 'Data', f'{domain}.3dvarfgat_pseudo.incr.{mdate}.nc'),
                           os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.{domain}.incr.nc')])

    # Copy the analysis at the start of the window
    post_file_list.append([os.path.join(anl_dir, 'Data', f'{domain}.3dvarfgat_pseudo.an.{mdate}.nc'),
                           os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.{domain}ana.nc')])

# Copy of the ssh diagnostics
'''
if nmem_ens > 2:
    for string in ['ssh_steric_stddev', 'ssh_unbal_stddev', 'ssh_total_stddev', 'steric_explained_variance']:
        post_file_list.append([os.path.join(anl_dir, 'static_ens', f'ocn.{string}.incr.{bdate}.nc'),
                               os.path.join(com_ocean_analysis, f'{RUN}.t{cyc}z.ocn.{string}.nc')])

# Copy DA grid (computed for the start of the window)
post_file_list.append([os.path.join(anl_dir, 'soca_gridspec.nc'),
                       os.path.join(com_ocean_analysis, f'{RUN}.t{bcyc}z.ocngrid.nc')])
'''

# Copy the CICE analysis restart
if os.getenv('DOIAU') == "YES":
    cice_rst_date = bdatedt.strftime('%Y%m%d.%H%M%S')
else:
    cice_rst_date = cdatedt.strftime('%Y%m%d.%H%M%S')

post_file_list.append([os.path.join(anl_dir, 'Data', f'{cice_rst_date}.cice_model.res.nc'),
                       os.path.join(com_ice_analysis, f'{cice_rst_date}.cice_model_anl.res.nc')])

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

# obs space statistics
logger.info(f"---------------- Compute basic stats")
diags_list = glob.glob(os.path.join(os.path.join(com_ocean_analysis, 'diags', '*.nc4')))
obsstats_j2yaml = str(os.path.join(os.getenv('HOMEgfs'), 'sorc', 'gdas.cd',
                                   'parm', 'soca', 'obs', 'obs_stats.yaml.j2'))


# function to create a minimalist ioda obs sapce
def create_obs_space(data):
    os_dict = {"obs space": {
               "name": data["obs_space"],
               "obsdatain": {
                   "engine": {"type": "H5File", "obsfile": data["obsfile"]}
               },
               "simulated variables": [data["variable"]]
               },
               "variable": data["variable"],
               "experiment identifier": data["pslot"],
               "csv output": data["csv_output"]
               }
    return os_dict


# attempt to extract the experiment id from the path
pslot = os.path.normpath(com_ocean_analysis).split(os.sep)[-5]

# iterate through the obs spaces and generate the yaml for gdassoca_obsstats.x
obs_spaces = []
for obsfile in diags_list:

    # define an obs space name
    obs_space = re.sub(r'\.\d{10}\.nc4$', '', os.path.basename(obsfile))

    # get the variable name, assume 1 variable per file
    nc = netCDF4.Dataset(obsfile, 'r')
    variable = next(iter(nc.groups["ObsValue"].variables))
    nc.close()

    # filling values for the templated yaml
    data = {'obs_space': os.path.basename(obsfile),
            'obsfile': obsfile,
            'pslot': pslot,
            'variable': variable,
            'csv_output': os.path.join(com_ocean_analysis,
                                       f"{RUN}.t{cyc}z.ocn.{obs_space}.stats.csv")}
    obs_spaces.append(create_obs_space(data))

# create the yaml
data = {'obs_spaces': obs_spaces}
conf = parse_j2yaml(path=obsstats_j2yaml, data=data)
stats_yaml = 'diag_stats.yaml'
conf.save(stats_yaml)

# run the application
# TODO(GorA): this should be setup properly in the g-w once gdassoca_obsstats is in develop
gdassoca_obsstats_exec = os.path.join(os.getenv('HOMEgfs'),
                                      'sorc', 'gdas.cd', 'build', 'bin', 'gdassoca_obsstats.x')
command = f"{os.getenv('launcher')} -n 1 {gdassoca_obsstats_exec} {stats_yaml}"
logger.info(f"{command}")
result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# issue a warning if the process has failed
if result.returncode != 0:
    logger.warning(f"{command} has failed")
if result.stderr:
    print("STDERR:", result.stderr.decode())
