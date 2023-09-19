#!/usr/bin/env python3

import os
from wxflow import YAMLFile
import prep_marine_obs

OBS_YAML = os.getenv('OBS_YAML')
print("OBS_YAML:", OBS_YAML)

data = YAMLFile(OBS_YAML)

# The following loop tries to find classes in prep_marine_obs corresponding
# to the observer names (traditionally of the form sensor_platform) with "_obs"
# appended, intantiate them, and then call their respective methods

for observer in data['observers']:
    obs_source_name = observer['obs space']['name']
    print(obs_source_name)
    obs_source_name = obs_source_name + '_obs'
    try:
        obs_source = getattr(prep_marine_obs, obs_source_name)
    except AttributeError:
        print("WARNING: No class", obs_source_name, "in prep_marine_obs")
        continue
    obs_set = obs_source()
    obs_set.fetch()
    obs_set.convert()
    obs_set.concatenate()
