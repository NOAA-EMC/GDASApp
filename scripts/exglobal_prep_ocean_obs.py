#!/usr/bin/env python3
# exglobal_prep_ocean_obs.py
# This script instantiates a PrepOceanObs class
# and runs the initialize, run, and finalize methods
import os

from wxflow import Logger, cast_strdict_as_dtypedict
from soca.prep_ocean_obs import PrepOceanObs

# Initialize root logger
logger = Logger(level='DEBUG', colored_log=True)

OBSFORGE_OBS_DB = True
OBSFORGE_DMPDIR = '/work2/noaa/da/gvernier/runs/obsForge/runobsf/COMROOT/obsforge'

if __name__ == '__main__':
    # Take configuration from environment and cast it as python dictionary
    config = cast_strdict_as_dtypedict(os.environ)

    prepOcnObs = PrepOceanObs(config)
    if OBSFORGE_OBS_DB:
        prepOcnObs.copy_from_obsforge(dmpdir=OBSFORGE_DMPDIR)
    else:
        prepOcnObs.initialize()
        prepOcnObs.run()
        prepOcnObs.finalize()
