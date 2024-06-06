#!/usr/bin/env python3

import argparse
import json
import os
from combine_base import Bufr2IodaBase
from wxflow import Logger

logger = Logger(os.path.basename(__file__), level='INFO')

yaml_file = "bufr2ioda_atms.yaml"
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

encoder = {
    'backend': 'netcdf',
    'dimensions': [{'name': 'Channel',
                    'path': '*/ATMSCH',
                    'source': 'variables/sensorChannelNumber'}],
    'globals': [{'name': 'platformCommonName',
                 'type': 'string',
                 'value': 'ATMS'},
                {'name': 'platformLongDescription',
                 'type': 'string',
                 'value': 'MTYP 021-203 ATMS '
                          'ATENNA/BRIGHTNESS '
                          'TEMPERATURE DATA'}],
    'obsdataout': 'atms_{splits/satId}_1716389684.nc',
    'variables': [{'longName': 'Datetime',
                   'name': 'MetaData/dateTime',
                   'source': 'variables/timestamp',
                   'units': 'seconds since '
                            '1970-01-01T00:00:00Z'},
                  {'longName': 'Latitude',
                   'name': 'MetaData/latitude',
                   'range': [-90, 90],
                   'source': 'variables/latitude',
                   'units': 'degree_north'},
                  {'longName': 'Longitude',
                   'name': 'MetaData/longitude',
                   'source': 'variables/longitude',
                   'units': 'degree_east'},
                  {'longName': 'Satellite Identifier',
                   'name': 'MetaData/satelliteIdentifier',
                   'source': 'variables/satelliteIdentifier'},
                  {'longName': 'Satellite Instrument',
                   'name': 'MetaData/satelliteInstrument',
                   'source': 'variables/satelliteInstrument'},
                  {'longName': 'Field of View Number',
                   'name': 'MetaData/sensorScanPosition',
                   'source': 'variables/fieldOfViewNumber'},
                  {'longName': 'Sensor View Angle',
                   'name': 'MetaData/sensorViewAngle',
                   'source': 'variables/sensorScanAngle',
                   'units': 'degree'},
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
                  {'longName': 'Sensor Channel Number',
                   'name': 'MetaData/sensorChannelNumber',
                   'source': 'variables/sensorChannelNumber'},
                  {'chunks': [10000, 22],
                   'longName': '3-by-3 Averaged '
                               'Brightness Temperature',
                   'name': 'ObsValue/brightnessTemperature',
                   'source': 'variables/remappedBT',
                   'units': 'K'}]},
bufr = {
    'splits': {'satId': {'category': {'map': {'_224': 'npp',
                                                           '_225': 'n20'},
                                                   'variable': 'satelliteIdentifier'}}},
    'variables': {
        'fieldOfViewNumber': {'query': '*/FOVN'},
        'heightOfStation': {'query': '*/HMSL'},
        'latitude': {'query': '*/CLATH'},
        'longitude': {'query': '*/CLONH'},
        'remappedBT': {'remappedBrightnessTemperature': {'brightnessTemperature': '*/ATMSCH/TMANT',
                                                        'fieldOfViewNumber': '*/FOVN',
                                                        'obsTime': {'day': '*/DAYS',
                                                                    'hour': '*/HOUR',
                                                                    'minute': '*/MINU',
                                                                    'month': '*/MNTH',
                                                                    'second': '*/SECO',
                                                                    'year': '*/YEAR'},
                                                        'sensorChannelNumber': '*/ATMSCH/CHNM'}},
        'satelliteIdentifier': {'query': '*/SAID'},
        'satelliteInstrument': {'query': '*/SIID'},
        'sensorAzimuthAngle': {'query': '*/BEARAZ'},
        'sensorChannelNumber': {'query': '*/ATMSCH/CHNM'},
        'sensorScanAngle': {'sensorScanAngle': {'fieldOfViewNumber': '*/FOVN',
                                               'scanStart': -52.725,
                                               'scanStep': 1.11,
                                               'sensor': 'atms'}},
        'sensorZenithAngle': {'query': '*/SAZA'},
        'solarAzimuthAngle': {'query': '*/SOLAZI'},
        'solarZenithAngle': {'query': '*/SOZA'}
    },
    'obsdatain': '/work2/noaa/da/xinjin/gdas-validation/global-workflow/sorc/gdas.cd/ush/ioda/bufr2ioda/gdas.t00z.atms.tm00.bufr_d',
}


class Bufr2IodaAtms(Bufr2IodaBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_config(config_json)
        self.yaml_config = dict(bufr=bufr, encoder=encoder)


