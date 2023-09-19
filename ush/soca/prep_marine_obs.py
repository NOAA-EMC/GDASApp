#!/usr/bin/env python3

from wxflow import FileHandler, YAMLFile
from datetime import datetime, timedelta
import os
import yaml
import fnmatch


class ocean_observation:

    DMPDIR = os.getenv('DMPDIR')
    cyc = os.getenv('cyc')
    PDY = os.getenv('PDY')
    CDUMP = os.getenv('CDUMP')
    COMIN_OBS = os.getenv('COMIN_OBS')

# Variables of convenience - raided from scripts/exgdas_global_marine_analysis_prep.py
    half_assim_freq = timedelta(hours=int(os.getenv('assim_freq'))/2)
    window_length = timedelta(hours=int(os.getenv('assim_freq')))
    window_middle = datetime.strptime(PDY+cyc, '%Y%m%d%H')
    window_begin = datetime.strptime(PDY+cyc, '%Y%m%d%H') - half_assim_freq
    window_end = datetime.strptime(PDY+cyc, '%Y%m%d%H') + half_assim_freq
    window_begin_iso = window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
    window_middle_iso = window_middle.strftime('%Y-%m-%dT%H:%M:%SZ')
    fcst_begin = datetime.strptime(PDY+cyc, '%Y%m%d%H')

    def __init__(self):

        self.cycdir = os.path.join(self.DMPDIR, self.CDUMP + '.' + str(self.PDY), str(self.cyc))

    def fetch(self, subdir, filepattern):

        datadir = os.path.join(self.cycdir, subdir)
        # TODO: check the existence of this
        print('datadir:', datadir)
        matching_files = []

        for root, _, files in os.walk(datadir):
            for filename in fnmatch.filter(files, filepattern):
                matching_files.append((root, filename))

        obs_cpy = []
        for obs_src in matching_files:
            obs_path = os.path.join(obs_src[0], obs_src[1])
            obs_dst = os.path.join(self.COMIN_OBS, obs_src[1])
            obs_cpy.append([obs_path, obs_dst])

        print(obs_cpy)

        FileHandler({'copy': obs_cpy}).sync()

    def convert(self):
        # Call ioda converter
        pass

    def concatenate(self):
        pass


class adt_j2_obs(ocean_observation):

    def __init__(self):
        super().__init__()

    def fetch(self):
        
        subdir='ADT'
#                   'rads_adt_j2_2021182.nc'
        filepattern='rads_adt_j2_???????.nc'

        super().fetch(subdir, filepattern)

    def convert(self):
        # Call ioda converter 
        pass

    def concatenate(self):

        pass


class adt_j3_obs(ocean_observation):

    def __init__(self):
        super().__init__()

    def fetch(self):
        
        subdir='ADT'
#                   'rads_adt_j3_2021182.nc'
        filepattern='rads_adt_j3_???????.nc'

        super().fetch(subdir, filepattern)

    def convert(self):
        # Call ioda converter 
        pass

    def concatenate(self):

        pass


class icec_amsr2_north_obs(ocean_observation):

    def __init__(self): 
        super().__init__() 

    def fetch(self):
        
        subdir='icec'
#       'AMSR2-SEAICE-NH_v2r2_GW1_s202107011426180_e202107011605170_c202107011642250.nc'
        filepattern='AMSR2-SEAICE-NH_v2r2_GW1_s???????????????_e???????????????_c???????????????.nc'

        super().fetch(subdir, filepattern)

    def convert(self):
        # Call ioda converter 
        pass

    def concatenate(self):

        pass


class icec_amsr2_south_obs(ocean_observation):

    def __init__(self):
        super().__init__()

    def fetch(self):
        
        subdir='icec'
#                   'AMSR2-SEAICE-SH_v2r2_GW1_s202107011426180_e202107011605170_c202107011642250.nc'
        filepattern='AMSR2-SEAICE-SH_v2r2_GW1_s???????????????_e???????????????_c???????????????.nc'

        super().fetch(subdir, filepattern)

    def convert(self):
        # Call ioda converter 
        pass

    def concatenate(self):

        pass


class sss_smap_obs(ocean_observation):

    def __init__(self):
        super().__init__()

    def fetch(self):
        
        subdir='SSS'
#                   'SMAP_L2B_SSS_NRT_34268_A_20210701T153914.h5'
        filepattern='SMAP_L2B_SSS_NRT_?????_[AD]_????????T??????.h5'

        super().fetch(subdir, filepattern)

    def convert(self):
        # Call ioda converter 
        pass

    def concatenate(self):

        pass
