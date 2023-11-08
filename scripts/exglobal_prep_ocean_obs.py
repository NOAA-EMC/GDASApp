#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# Pepares observations for marine DA
import os
from wxflow import YAMLFile
import prep_marine_obs
import logging
import subprocess

OBS_YAML = os.getenv('OBS_YAML')

data = YAMLFile(OBS_YAML)
print(data)

for observer in data['observers']:
    obs_source_name = observer['obs space']['name']
    logging.info(f"obs_source_name: {obs_source_name}")
    prep_marine_obs.obs_fetch(obs_source_name)

# TODO (AFE): ideally this should be an env var
obsprocexec = "/scratch1/NCEPDEV/da/Andrew.Eichmann/fv3gfs/newoceaanobs/global-workflow/sorc/gdas.cd/build/bin/gdas_obsprovider2ioda.x"

# TODO (AFE): to be selected according to obs source? dynamically generate, so...
obsprocyaml = "/scratch1/NCEPDEV/da/Andrew.Eichmann/fv3gfs/newoceaanobs/global-workflow/sorc/gdas.cd/gdas_smap2ioda.yaml"

subprocess.run([obsprocexec, obsprocyaml], check=True)


