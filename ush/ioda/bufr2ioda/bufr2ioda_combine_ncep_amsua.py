#!/usr/bin/env python3
import argparse
import json
import os
from combine_base import Bufr2IodaBase
from wxflow import Logger, save_as_yaml
from antcorr_application import ACCoeff, apply_ant_corr, remove_ant_corr, R1000, R1000000
from utils import timing_decorator

logger = Logger(os.path.basename(__file__), level='INFO')
AMSUA_TYPE_CHANGE_DATETIME = "20231200"
BAMUA = '1BAMUA'
ESAMUA = 'ESAMUA'

YAML_NORMAL = True  # current as normal

yaml_1b_file = "bufr2ioda_ncep_1bamua_ta.yaml"
yaml_es_file = "bufr2ioda_ncep_esamua.yaml"

config = {
    'RUN': 123,
    'current_cycle': '2022010412',
    'DATA': 'abcd',
    'DMPDIR': 'abc',
    'COM_OBS': 'abs',
    'PDY': '20220104',
    'cyc': '12',
}

config_json = {
    "subsets": ["NC005030", "NC005031", "NC005032", "NC005034", "NC005039"],
    "data_description": "NC005030 NESDIS SATWIND, GOES IR(LW);  NC005031 NESDIS SATWIND, GOES WV-IMG/DL; "
                        "NC005032 NESDIS SATWIND, GOES VIS; NC005034 NESDIS SATWIND, GOES WV-IMG/CT; "
                        "NC005039 NESDIS SATWIND, GOES IR(SW)",
    "data_provider": "U.S. NOAA/NDESDIS",
    "sensor_info": {"sensor_name": "ABI", "sensor_full_name": "Advanced Baseline Imager", "sensor_id": 617},
    "satellite_info": [
        {"satellite_name": "GOES-16", "satellite_full_name": "Geostationary Operational Satellite - 16",
         "satellite_id": 270},
        {"satellite_name": "GOES-17", "satellite_full_name": "Geostationary Operational Satellite - 17",
         "satellite_id": 271},
        {"satellite_name": "GOES-18", "satellite_full_name": "Geostationary Operational Satellite - 18",
         "satellite_id": 272}
    ],
    "yaml_file": [yaml_es_file, yaml_1b_file],
    "ac_dir": "./"
}

bufr = {
    'obsdatain': '/scratch2/NCEPDEV/stmp3/Xin.C.Jin/bufr2ioda/gdas.t00z.1bamua.tm00.bufr_d',
    'splits': {'satId': {'category': {'map': {'_209': 'n18',
                                              '_223': 'n19',
                                              '_3': 'metop-b',
                                              '_4': 'metop-a',
                                              '_5': 'metop-c'
                                              },
                                      'variable': 'satelliteIdentifier'
                                      }}},
    'variables': {'brightnessTemperature': {'query': '*/BRITCSTC/TMBR'},
                  'fieldOfViewNumber': {'query': '*/FOVN'},
                  'heightOfStation': {'query': '*/HMSL'},
                  'latitude': {'query': '*/CLAT'},
                  'longitude': {'query': '*/CLON'},
                  'satelliteIdentifier': {'query': '*/SAID'},
                  'sensorAzimuthAngle': {'query': '*/BEARAZ'},
                  'sensorChannelNumber': {'query': '*/BRITCSTC/CHNM'},
                  'sensorScanAngle': {'sensorScanAngle': {'fieldOfViewNumber': '*/FOVN',
                                                          'scanStart': -48.333,
                                                          'scanStep': 3.333,
                                                          'sensor': 'amsua'}},
                  'sensorZenithAngle': {'query': '*/SAZA'},
                  'solarAzimuthAngle': {'query': '*/SOLAZI'},
                  'solarZenithAngle': {'query': '*/SOZA'},
                  'timestamp': {'datetime': {'day': '*/DAYS',
                                             'hour': '*/HOUR',
                                             'minute': '*/MINU',
                                             'month': '*/MNTH',
                                             'year': '*/YEAR'}}}
}
encoder = {
    'backend': 'netcdf',
    'dimensions': [{'name': 'Channel',
                    'path': '*/BRITCSTC',
                    'source': 'variables/sensorChannelNumber'}],
    'globals': [{'name': 'platformCommonName',
                 'type': 'string',
                 'value': 'AMSU-A'},
                {'name': 'platformLongDescription',
                 'type': 'string',
                 'value': 'MTYP 021-023 PROC AMSU-A 1B Tb'}],
    'obsdataout': 'temporary_ta_{splits/satId}_1716389684.nc',
    'variables': [
          {'longName': 'Datetime',
                   'name': 'MetaData/dateTime',
                   'source': 'variables/timestamp',
                   'units': 'seconds since 1970-01-01T00:00:00Z'},
          {'longName': 'Latitude',
           'name': 'MetaData/latitude',
           'range': [-90, 90],
           'source': 'variables/latitude',
           'units': 'degree_north'},
          {'longName': 'Longitude',
           'name': 'MetaData/longitude',
           'range': [-180, 180],
           'source': 'variables/longitude',
           'units': 'degree_east'},
          {'longName': 'Satellite Identifier',
           'name': 'MetaData/satelliteIdentifier',
           'source': 'variables/satelliteIdentifier'},
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
          {'longName': 'Field of View Number',
           'name': 'MetaData/sensorScanPosition',
           'source': 'variables/fieldOfViewNumber'},
          {'chunks': [1000, 15],
           'compressionLevel': 4,
           'longName': 'Antenna Temperature',
           'name': 'ObsValue/brightnessTemperature',
           'range': [90, 380],
           'source': 'variables/brightnessTemperature',
           'units': 'K'}
    ]
}

yaml_1b = dict(bufr=bufr, encoder=encoder)

save_as_yaml(yaml_1b, yaml_1b_file)

yaml_es = {'bufr': {'obsdatain': '/scratch2/NCEPDEV/stmp3/Xin.C.Jin/bufr2ioda/gdas.t00z.esamua.tm00.bufr_d',
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
                        'solarZenithAngle': {'query': '*/SOZA'},
                        'timestamp': {'datetime': {'day': '*/DAYS',
                                                   'hour': '*/HOUR',
                                                   'minute': '*/MINU',
                                                   'month': '*/MNTH',
                                                   'year': '*/YEAR'}}}},
 'encoder': {'backend': 'netcdf',
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
             'variables': [{'longName': 'Datetime',
                            'name': 'MetaData/dateTime',
                            'source': 'variables/timestamp',
                            'units': 'seconds since 1970-01-01T00:00:00Z'},
                           {'longName': 'Latitude',
                            'name': 'MetaData/latitude',
                            'range': [-90, 90],
                            'source': 'variables/latitude',
                            'units': 'degree_north'},
                           {'longName': 'Longitude',
                            'name': 'MetaData/longitude',
                            'range': [-180, 180],
                            'source': 'variables/longitude',
                            'units': 'degree_east'},
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
                            'units': 'K'}]}}

save_as_yaml(yaml_es, yaml_es_file)


class Bufr2IodaAmusa(Bufr2IodaBase):
    def __init__(self, yaml_order, *args, **kwargs):
        self.yaml_order = yaml_order
        super().__init__(*args, **kwargs)
        self.config.update(config_json)

        if self.yaml_order:
            self.yaml_config = yaml_es
        else:
            self.yaml_config = yaml_1b

    def get_yaml_file(self):
        if self.yaml_order:
            return self.config['yaml_file'][0]
        else:
            return self.config['yaml_file'][1]


class Bufr2IodaAmusaChange(Bufr2IodaAmusa):
    def __init__(self, *args, **kwargs):
        self.yaml_order = args[0]
        super().__init__(*args, **kwargs)
        if self.yaml_order:
            self.yaml_config = yaml_1b
        else:
            self.yaml_config = yaml_es

    def get_yaml_file(self):
        if self.yaml_order:
            return self.config['yaml_file'][1]
        else:
            return self.config['yaml_file'][0]

    def get_ac_dir(self):
        return self.config['ac_dir']

    @timing_decorator
    def re_map_variable(self):
        #  TODO replace this follow that in GSI
        # read_bufrtovs.f90
        # antcorr_application.f90
        # search the keyword “ta2tb” for details

        for sat_id in self.sat_ids:
            logger.info(f'Converting for {sat_id}, ...')
            ta = self.get_container_variable('variables', 'brightnessTemperature', sat_id)
            if ta.shape[0]:
                ifov = self.get_container_variable('variables', 'fieldOfViewNumber', sat_id)
                logger.info(f'ta before correction1: {ta[:100, :]}')
                tb = self.apply_corr(sat_id, ta, ifov)
                logger.info(f'tb after correction1: {tb[:100, :]}')
                self.replace_container_variable('variables', 'brightnessTemperature', tb, sat_id)

    def apply_corr(self, sat_id, ta, ifov):
        ac = ACCoeff(self.get_ac_dir())  # TODO add later
        llll = 1  # TODO how to set this
        if llll == 1:
            if sat_id not in ['n15', 'n16']:
                # Convert antenna temperature to brightness temperature
                ifov = ifov.astype(int) - 1
                for i in range(ta.shape[1]):
                    logger.info(f'inside loop for allpy ta to tb: i = {i}')
                    x = ta[:, i]
                    # logger.info(f'ta before correction: {x[:100]}')
                    if self.yaml_order:
                        x = apply_ant_corr(i, ac, ifov, x)
                    else:
                        x = remove_ant_corr(i, ac, ifov, x)
                    # logger.info(f'ta after correction: {x[:100]}')
                    x[x >= R1000] = R1000000
                    ta[:, i] = x
        else:
            pass  # TODO after know how to set llll
        return ta


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # parser.add_argument('-c', '--config', type=str, help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()
    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger(os.path.basename(__file__), level=log_level)
    amsua_files = []
    splits = set()

    cycle_datetime = config["PDY"]
    if cycle_datetime >= AMSUA_TYPE_CHANGE_DATETIME:
        yaml_order = YAML_NORMAL
    else:
        yaml_order = not YAML_NORMAL
    logger.info(f'yaml order is {yaml_order}')

    convert_bamua = Bufr2IodaAmusa(yaml_order, config)
    convert_bamua.execute()
    convert_esamua = Bufr2IodaAmusaChange(yaml_order, config)
    convert_esamua.execute()

    logger.info('--Finished--')
