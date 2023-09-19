#!/usr/bin/env python3

import os
from wxflow import FileHandler, YAMLFile
import prep_marine_obs

OBS_YAML=os.getenv('OBS_YAML')
print("OBS_YAML:",OBS_YAML)

data = YAMLFile(OBS_YAML)

for observer in data['observers']:
   print(observer['obs space']['name'])
#adt_all
#adt_j3
#adt_j2
#sss_smap
#sst_noaa19_l3u
#icec_emc

#icec_amsr2_south_obs_set = prep.icec_amsr2_south_obs()
#icec_amsr2_south_obs_set.fetch()

obs_source = getattr(prep_marine_obs, 'icec_amsr2_north_obs')
obs_set=obs_source()
obs_set.fetch()

obs_source = getattr(prep_marine_obs, 'icec_amsr2_south_obs')
obs_set=obs_source()
obs_set.fetch()

