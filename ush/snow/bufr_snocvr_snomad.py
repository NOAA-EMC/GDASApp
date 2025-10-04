#!/usr/bin/env python3
import os
import numpy as np
import numpy.ma as ma
import json

import bufr
from bufr.obs_builder import ObsBuilder, add_main_functions, map_path

SNOCVR_MAPPING = map_path('bufr_snocvr_mapping.yaml')
SNOMAD_MAPPING = map_path('bufr_snomad_mapping.yaml')

SNOCVR = 'snocvr'
SNOMAD = 'snomad'


class BufrTotalSnowDepthObsBuilder(ObsBuilder):
    def __init__(self):

        map_dict = {SNOCVR: SNOCVR_MAPPING,
                    SNOMAD: SNOMAD_MAPPING}

        super().__init__(map_dict, log_name=os.path.basename(__file__))

    def create_obs_file(self, input_snocvr=None, output=None, input_snomad=None,
                        type='netcdf', append=False):
        from bufr.encoders import netcdf
        FILE_ENCODER_DICT = {'netcdf': netcdf.Encoder}

        comm = bufr.mpi.Comm("world")
        self.log.comm = comm

        input_dict = {}
        if input_snocvr and os.path.exists(input_snocvr):
            input_dict[SNOCVR] = input_snocvr
        else:
            self.log.warning("SNOCVR file missing or not provided, continuing with SNOMAD only.")

        if input_snomad and os.path.exists(input_snomad):
            input_dict[SNOMAD] = input_snomad
        else:
            self.log.warning("SNOMAD file missing or not provided.")

        if not input_dict:
            self.log.warning("No valid input files found (SNOCVR or SNOMAD). Nothing to process.")
            return None

        container = self.make_obs(comm, input_dict)
        container.gather(comm)

        # Encode the data
        if comm.rank() == 0:
            self.finalize_container(container)
            FILE_ENCODER_DICT[type](self.description).encode(container, output, append)

        self.log.info(f'Return the encoded data')

    def create_obs_group(self, input_snocvr=None, env=None, input_snomad=None):

        from pyioda.ioda.Engines.Bufr import Encoder as iodaEncoder

        comm = bufr.mpi.Comm(env["comm_name"])
        self.log.comm = comm

        input_dict = {}
        if input_snocvr and os.path.exists(input_snocvr):
            input_dict[SNOCVR] = input_snocvr
        else:
            self.log.warning("SNOCVR file missing or not provided, continuing with SNOMAD only.")

        if input_snomad and os.path.exists(input_snomad):
            input_dict[SNOMAD] = input_snomad
        else:
            self.log.warning("SNOMAD file missing or not provided.")

        if not input_dict:
            self.log.warning("No valid input files found (SNOCVR or SNOMAD). Nothing to process.")
            return None

        container = self.make_obs(comm, input_dict)
        container.all_gather(comm)

        self.finalize_container(container)

        # Encode the data
        self.log.info(f'Encoding')
        data = next(iter(iodaEncoder(self.description).encode(container).values()))

        return data

    def make_obs(self, comm, input_dict):

        self.log.info(f'Active mappings: {", ".join([self.map_dict[k] for k in input_dict.keys()])}')

        # Always start with the first available dataset
        first_key = next(iter(input_dict))
        container = bufr.Parser(input_dict[first_key], self.map_dict[first_key]).parse(comm)

        # If both are present, append the second
        for k in input_dict:
            if k != first_key:
                container.append(bufr.Parser(input_dict[k], self.map_dict[k]).parse(comm))

        self.log.debug(f'container list (combined): {container.list()}')

        return container


add_main_functions(BufrTotalSnowDepthObsBuilder)
