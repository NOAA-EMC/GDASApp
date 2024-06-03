#!/usr/bin/env python3
import argparse
import json
import os
from combine_base import Bufr2IodaBase
from wxflow import Logger, save_as_yaml
from antcorr_application import ACCoeff, apply_ant_corr, remove_ant_corr, R1000, R1000000
from utils import timing_decorator

logger = Logger(os.path.basename(__file__), level='INFO')

config_json = dict(yaml_file="bufr2ioda_ncep_esamua.yaml",
                   data_type="esamua",)

bufr = {'obsdatain': '/scratch2/NCEPDEV/stmp3/Xin.C.Jin/bufr2ioda/gdas.t00z.esamua.tm00.bufr_d',
          'splits': {'satId': {'category': {'map': {'_209': 'n18',
                                                    '_223': 'n19',
                                                    '_3': 'metop-b',
                                                    '_4': 'metop-a',
                                                    '_5': 'metop-c'},
                                            'variable': 'satelliteIdentifier'}}},
          'variables': {'brightnessTemperature': {'query': '*/ATNCHV/TMBRST'},
                        'fieldOfViewNumber': {'query': '*/FOVN'},
                        'heightOfStation': {'query': '*/SELV'},
                        'latitude': {'query': '*/CLATH'},
                        'longitude': {'query': '*/CLONH'},
                        'satelliteIdentifier': {'query': '*/SAID'},
                        'sensorAzimuthAngle': {'query': '*/BEARAZ'},
                        'sensorChannelNumber': {'query': '*/ATNCHV/INCN'},
                        'sensorScanAngle': {'sensorScanAngle': {'fieldOfViewNumber': '*/FOVN',
                                                                'scanStart': -48.333,
                                                                'scanStep': 3.333,
                                                                'sensor': 'amsua'}},
                        'sensorZenithAngle': {'query': '*/SAZA'},
                        'solarAzimuthAngle': {'query': '*/SOLAZI'},
                        'solarZenithAngle': {'query': '*/SOZA'}}}

encoder = {'backend': 'netcdf',
             'dimensions': [{'name': 'Channel',
                             'path': '*/ATNCHV',
                             'source': 'variables/sensorChannelNumber'}],
             'globals': [{'name': 'platformCommonName',
                          'type': 'string',
                          'value': 'AMSUA'},
                         {'name': 'platformLongDescription',
                          'type': 'string',
                          'value': 'MTYP 021-033 RARS(EARS,AP,SA) AMSU-A 1C Tb '
                                   'DATA)'}],
             'obsdataout': 'temporary_es_{splits/satId}_1716389684.nc',
             'variables': [
                           {'longName': 'Satellite Identifier',
                            'name': 'MetaData/satelliteIdentifier',
                            'source': 'variables/satelliteIdentifier'},
                           {'longName': 'Field Of View Number',
                            'name': 'MetaData/sensorScanPosition',
                            'source': 'variables/fieldOfViewNumber'},
                           {'longName': 'Altitude of Satellite',
                            'name': 'MetaData/heightOfStation',
                            'source': 'variables/heightOfStation',
                            'units': 'm'},
                           {'longName': 'Solar Zenith Angle',
                            'name': 'MetaData/solarZenithAngle',
                            'range': [0, 180],
                            'source': 'variables/solarZenithAngle',
                            'units': 'degree'},
                           {'longName': 'Solar Azimuth Angle',
                            'name': 'MetaData/solarAzimuthAngle',
                            'range': [0, 360],
                            'source': 'variables/solarAzimuthAngle',
                            'units': 'degree'},
                           {'longName': 'Sensor Zenith Angle',
                            'name': 'MetaData/sensorZenithAngle',
                            'range': [0, 90],
                            'source': 'variables/sensorZenithAngle',
                            'units': 'degree'},
                           {'longName': 'Sensor Azimuth Angle',
                            'name': 'MetaData/sensorAzimuthAngle',
                            'range': [0, 360],
                            'source': 'variables/sensorAzimuthAngle',
                            'units': 'degree'},
                           {'longName': 'Sensor View Angle',
                            'name': 'MetaData/sensorViewAngle',
                            'source': 'variables/sensorScanAngle',
                            'units': 'degree'},
                           {'longName': 'Sensor Channel Number',
                            'name': 'MetaData/sensorChannelNumber',
                            'source': 'variables/sensorChannelNumber'},
                           {'chunks': [1000, 15],
                            'compressionLevel': 4,
                            'coordinates': 'longitude latitude Channel',
                            'longName': 'Brightness Temperature',
                            'name': 'ObsValue/brightnessTemperature',
                            'range': [100, 500],
                            'source': 'variables/brightnessTemperature',
                            'units': 'K'}]}


class Bufr2IodaEsamusa(Bufr2IodaBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config.update(config_json)
        self.yaml_config = dict(bufr=bufr, encoder=encoder)
