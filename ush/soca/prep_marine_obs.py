#!/usr/bin/env python3

from wxflow import FileHandler, YAMLFile
from datetime import datetime, timedelta
import os
import yaml
import fnmatch

#COM_OBSDMP_TMPL=getenv('COM_OBSDMP_TMPL')
#print(COM_OBSDMP_TMPL)
COM_OBSDMP=os.getenv('COM_OBSDMP')
OBS_YAML=os.getenv('OBS_YAML')
print("COM_OBSDMP:",COM_OBSDMP)
print("OBS_YAML:",OBS_YAML)
COM_OBSDMP_BASE='/scratch1/NCEPDEV/stmp4/Shastri.Paturi/forAndrew/'

# Variables of convenience - raided from scripts/exgdas_global_marine_analysis_prep.py
RUN = os.getenv('RUN')
cyc = os.getenv('cyc')
PDY = os.getenv('PDY')
CDUMP = os.getenv('CDUMP')
#DUMP = 'gdas'
#PDY = '20210701'
#cyc = '12'
half_assim_freq = timedelta(hours=int(os.getenv('assim_freq'))/2)
window_middle = datetime.strptime(PDY+cyc, '%Y%m%d%H')
window_begin = datetime.strptime(PDY+cyc, '%Y%m%d%H') - half_assim_freq
window_end = datetime.strptime(PDY+cyc, '%Y%m%d%H') + half_assim_freq
window_begin_iso = window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
window_middle_iso = window_middle.strftime('%Y-%m-%dT%H:%M:%SZ')
fcst_begin = datetime.strptime(PDY+cyc, '%Y%m%d%H')

print('window_middle:',window_middle)
print('window_middle_iso:',window_middle_iso)
print('PDY:',PDY)
print('cyc:',cyc)

data = YAMLFile(OBS_YAML)

for observer in data['observers']:
   print(observer['obs space']['name'])


#           'AMSR2-SEAICE-NH_v2r2_GW1_s202107011426180_e202107011605170_c202107011642250.nc'
filepattern='AMSR2-SEAICE-NH_v2r2_GW1_s???????????????_e???????????????_c???????????????.nc'
subdir='icec'

cycdir=os.path.join(COM_OBSDMP_BASE,CDUMP + '.' + str(PDY), str(cyc))
datadir=os.path.join(cycdir,subdir)
#TODO: check the existence of this
print('datadir:',datadir)
matching_files=[]

for root, _, files in os.walk(datadir):
    for filename in fnmatch.filter(files, filepattern):
        matching_files.append(os.path.join(root, filename))

# Print the list of matching files
for file_path in matching_files:
    print(file_path)



class OceanObservations:
    def __init__(self, window_begin, window_length, DMPDIR, COM_OBS):
        self.window_begin = window_begin
        self.window_length = window_length
        self.DMPDIR = DMPDIR
        self.COM_OBS = COM_OBS



FileHandler({'copy': post_file_list}).sync()    
