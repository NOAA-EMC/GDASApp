#!/usr/bin/env python3
import os
from combine_base import Bufr2IodaBase
from wxflow import Logger, save_as_yaml
from antcorr_application import ACCoeff, apply_ant_corr, remove_ant_corr, R1000, R1000000
from utils import timing_decorator

logger = Logger(os.path.basename(__file__), level='INFO')
AMSUA_TYPE_CHANGE_DATETIME = "20231200"
BAMUA = '1BAMUA'
ESAMUA = 'ESAMUA'

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
    "ac_dir": "./"
}


class Bufr2IodaAmusaBase(Bufr2IodaBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config.update(config_json)
        self.cycle_datetime = self.config["PDY"]

        # if self.yaml_order:
        #     self.yaml_config = yaml_es
        # else:
        #     self.yaml_config = yaml_1b

    def get_ac_dir(self):
        return self.config['ac_dir']

    @timing_decorator
    def re_map_variable(self):
        if self.cycle_datetime > AMSUA_TYPE_CHANGE_DATETIME and self.data_type == ESAMUA:
            return

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
