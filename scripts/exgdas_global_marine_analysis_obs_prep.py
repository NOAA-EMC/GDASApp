#!/usr/bin/env python3

import os
from wxflow import YAMLFile
import prep_marine_obs

OBS_YAML=os.getenv('OBS_YAML')
print("OBS_YAML:",OBS_YAML)

data = YAMLFile(OBS_YAML)

# The following loop tries to find classes in prep_marine_obs corresponding
# to the observer names with "_obs" appended, intantiate them, and then
# call their respective methods

# obs_source_name should look like:
#adt_all
#adt_j3
#adt_j2
#sss_smap
#sst_noaa19_l3u
#icec_emc

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


# the following are for testing - not in soca ctest OBS_YAML, but files available

observers = ['icec_amsr2_north',
             'icec_amsr2_south',
             'sst_viirs_n20_l3u_so025',
             'sst_viirs_npp_l3u_so025',
             'sst_metopa_l3u_so025',
             'sst_metopb_l3u_so025']

for obs_source_name in observers:
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


