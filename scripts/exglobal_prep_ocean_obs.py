#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# Pepares observations for marine DA
import os
from wxflow import YAMLFile
import prep_marine_obs
import logging
import subprocess

# set up logger
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')

OBS_YAML = os.getenv('OBS_YAML')

obsConfig = YAMLFile(OBS_YAML)
print(obsConfig)

for observer in obsConfig['observers']:
    obsSpaceName = observer['obs space']['name']
    #logging.info(f"obsSpaceName: {obsSpaceName}")
    print(f"obsSpaceName: {obsSpaceName}")
    prep_marine_obs.obs_fetch(obsSpaceName)

# TODO (AFE): ideally this should be an env var
obsprocexec = "/scratch1/NCEPDEV/da/Andrew.Eichmann/fv3gfs/newoceaanobs/global-workflow/sorc/gdas.cd/build/bin/gdas_obsprovider2ioda.x"

# TODO (AFE): to be selected according to obs source? dynamically generate, so...
obsprocyaml = "/scratch1/NCEPDEV/da/Andrew.Eichmann/fv3gfs/newoceaanobs/global-workflow/sorc/gdas.cd/gdas_smap2ioda.yaml"

subprocess.run([obsprocexec, obsprocyaml], check=True)


