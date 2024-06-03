#!/usr/bin/env python3

import argparse
import json
import os
from combine_base import Bufr2IodaBase
from wxflow import Logger

logger = Logger(os.path.basename(__file__), level='INFO')

yaml_file = "bufr2ioda_ssmis.yaml"
config_json = {
    "data_type": "ssmis",
    "subsets": ["NC005044", "NC005045", "NC005046"],
    "data_description": "NC005044 JMA SATWIND, AHI HIM8 IR(LW)/VIS/WV-CT/WV-CS;  NC005045 JMA SATWIND, HIMAWARI-8 "
                        "IR(LW)/VIS/WV-CT/WV-CS; NC005046 JMA SATWIND, HIMAWARI-8 IR(LW)/VIS/WV-CT/WV-CS",
    "data_provider": "JMA",
    "sensor_info": {"sensor_name": "AHI", "sensor_full_name": "Advanced Himawari Imager", "sensor_id": 999},
    "satellite_info": [
        {"satellite_name": "GOES-16", "satellite_full_name": "Geostationary Operational Satellite - 16",
         "satellite_id": 249},
        {"satellite_name": "GOES-17", "satellite_full_name": "Geostationary Operational Satellite - 17",
         "satellite_id": 285},
        {"satellite_name": "GOES-18", "satellite_full_name": "Geostationary Operational Satellite - 18",
         "satellite_id": 286},
        {"satellite_name": "GOES-18", "satellite_full_name": "Geostationary Operational Satellite - 18",
         "satellite_id": 287}
    ],
    "yaml_file": yaml_file
}

ssmis_yaml = {
    'bufr': {
#        obsdatain: "{{ DMPDIR }}/{{ RUN }}.{{ PDY }}/{{ cyc }}/atmos/{{ RUN }}.t{{ cyc }}z.esamua.tm00.bufr_d"
 
        'obsdatain': '/scratch2/NCEPDEV/stmp3/Xin.C.Jin/bufr2ioda/from_orion/gdas.t00z.ssmisu.tm00.bufr_d',
        'splits': {'satId': {'category': {'map': {'_249': 'f16',
                                                  '_285': 'f17',
                                                  '_286': 'f18',
                                                  '_287': 'f19'},
                                          'variable': 'satelliteIdentifier'}}},
        'variables': {
            'fieldOfViewNumber': {'query': '*/FOVN'},
            'latitude': {'query': '*/CLAT'},
            'longitude': {'query': '*/CLON'},
            'orbitNumber': {'query': '*/ORBN'},
            'rainFlag': {'query': '*/RFLAG'},
            'remappedBT': {'remappedBrightnessTemperature': {'brightnessTemperature': '*/SSMISCHN/TMBR',
                                                             'fieldOfViewNumber': '*/FOVN',
                                                             'obsTime': {'day': '*/DAYS',
                                                                         'hour': '*/HOUR',
                                                                         'minute': '*/MINU',
                                                                         'month': '*/MNTH',
                                                                         'second': '*/SECO',
                                                                         'year': '*/YEAR'},
                                                             'sensorChannelNumber': '*/SSMISCHN/CHNM'}},
            'satelliteIdentifier': {'query': '*/SAID'},
            'scanLineNumber': {'query': '*/SLNM'},
            'sensorChannelNumber': {'query': '*/SSMISCHN/CHNM'},
            'surfaceFlag': {'query': '*/SFLG'}
        }},
    'encoder': {
        'dimensions': [{'name': 'Channel',
                        'path': '*/SSMISCHN',
                        'source': 'variables/sensorChannelNumber'}],
        'globals': [{'name': 'platformCommonName',
                     'type': 'string',
                     'value': 'SSMIS'},
                    {'name': 'platformLongDescription',
                     'type': 'string',
                     'value': 'MTYP 021-203 SSMIS ATENNA/BRIGHTNESS '
                              'TEMPERATURE DATA'}],
#        obsdataout: "{{ COM_OBS }}/{{ RUN }}.t{{ cyc }}z.esamua.$(splitvar).tm00.nc"
        'obsdataout': 'temporary_{splits/satId}_1716389684.nc',
        'variables': [{'longName': 'Satellite Identifier',
                       'name': 'MetaData/satelliteIdentifier',
                       'source': 'variables/satelliteIdentifier'},
                      {'longName': 'Sensor Channel Number',
                       'name': 'MetaData/sensorChannelNumber',
                       'source': 'variables/sensorChannelNumber'},
                      {'chunks': [10000, 22],
                       'longName': '3-by-3 Averaged Brightness '
                                   'Temperature',
                       'name': 'ObsValue/brightnessTemperature',
                       'source': 'variables/remappedBT',
                       'units': 'K'}]}}

# This will be moved out in the future. it should be an input when call this program.


class Bufr2IodaSsmis(Bufr2IodaBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_config(config_json)
        self.yaml_config = ssmis_yaml


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()
    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger(os.path.basename(__file__), level=log_level)
    converter = Bufr2IodaSsmis(config)
    converter.execute()
    logger.info('--Finished--')
