#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# This script creates an PrepOceanObs class
# and runs the initialize, run, and finalize  methods
import os

from wxflow import Logger, cast_strdict_as_dtypedict
from soca.prep_ocean_obs import PrepOceanObs

# Initialize root logger
logger = Logger(level='DEBUG', colored_log=True)


if __name__ == '__main__':

    # Take configuration from environment and cast it as python dictionary
    config = cast_strdict_as_dtypedict(os.environ)

    # Instantiate the aerosol analysis task
    PrepOcnObs = PrepOceanObs(config)
    PrepOcnObs.initialize()
    PrepOcnObs.run()
    PrepOcnObs.finalize()
