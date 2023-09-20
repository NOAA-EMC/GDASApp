#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# Pepares observations for coupled ocean DA
import os
from wxflow import YAMLFile
import prep_marine_obs

OBS_YAML = os.getenv('OBS_YAML')
print("OBS_YAML:", OBS_YAML)

data = YAMLFile(OBS_YAML)
print(data)

for observer in data['observers']:
    obs_source_name = observer['obs space']['name']
    print(obs_source_name)
    prep_marine_obs.obs_fetch(obs_source_name)
