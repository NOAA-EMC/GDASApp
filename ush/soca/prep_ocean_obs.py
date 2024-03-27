#!/usr/bin/env python3

from datetime import datetime, timedelta
import f90nml
from logging import getLogger
import os
from soca import bkg_utils
from typing import Dict
import ufsda
from ufsda.stage import soca_fix
from wxflow import (AttrDict,
                    chdir,
                    Executable,
                    FileHandler,
                    logit,
                    parse_j2yaml,
                    Task,
                    Template,
                    TemplateConstants,
                    WorkflowException,
                    YAMLFile)

logger = getLogger(__name__.split('.')[-1])


class PrepOceanObs(Task):
    """
    Class for prepping obs for ocean analysis task
    """

    @logit(logger, name="PrepOceanObs")
    def __init__(self, config: Dict) -> None:
        """Constructor for ocean obs prep task
        Parameters:
        ------------
        config: Dict
            configuration, namely evironment variables
        Returns:
        --------
        None
        """

        logger.info("init")
        super().__init__(config)

        PDY = self.runtime_config['PDY']
        cyc = self.runtime_config['cyc']
        DATA = self.runtime_config.DATA

        # Set the window times
        cdate = datetime.strptime(PDY + cyc, '%Y%m%d%H')
        self.runtime_config['cdate'] = cdate
        windowBeginDatetime = cdate - timedelta(hours=3)
        windowEndDatetime = cdate + timedelta(hours=3)
        windowBegin = windowBeginDatetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        windowEnd = windowEndDatetime.strftime('%Y-%m-%dT%H:%M:%SZ')

    @logit(logger)
    def initialize(self):
        """Method initialize for ocean obs prep task
        Parameters:
        ------------
        None
        Returns:
        --------
        None
        """

        logger.info("initialize")

        cdate = self.runtime_config['cdate']

        OBS_YAML = self.config['OBS_YAML']
        obsConfig = YAMLFile(OBS_YAML)

        OBSPREP_YAML = self.config['OBSPREP_YAML']
        if os.path.exists(OBSPREP_YAML):
            obsprepConfig = YAMLFile(OBSPREP_YAML)
        else:
            logger.critical(f"OBSPREP_YAML file {OBSPREP_YAML} does not exist")
            raise FileNotFoundError

        COMOUT_OBS = self.config['COMOUT_OBS']
        if not os.path.exists(COMOUT_OBS):
            os.makedirs(COMOUT_OBS)
    
        files_to_save = []
        obsspaces_to_convert = []
        
        try:
            # go through the sources in OBS_YAML
            for observer in obsConfig['observers']:
                try:
                    obs_space_name = observer['obs space']['name']
                    logger.info(f"obsSpaceName: {obs_space_name}")
                except KeyError:
                    logger.warning(f"observer: {observer}")
                    logger.warning("Ill-formed observer yaml file, skipping")
                    continue
        
                # find match to the obs space from OBS_YAML in OBSPREP_YAML
                # this is awkward and unpythonic, so feel free to improve
                for observation in obsprepConfig['observations']:
                    obsprepSpace = observation['obs space']
                    obsprepSpaceName = obsprepSpace['name']
        
                    if obsprepSpaceName == obs_space_name:
                        logger.info(f"obsprepSpaceName: {obs_space_name}")
        
                        try:
                            obsWindowBack = obsprepSpace['window']['back']
                            obsWindowForward = obsprepSpace['window']['forward']
                        except KeyError:
                            obsWindowBack = 0
                            obsWindowForward = 0
        
                        cycles = []
                        for i in range(-obsWindowBack, obsWindowForward + 1):
                            interval = timedelta(hours=6 * i)
                            cycles.append(cdate + interval)
        
                        matchingFiles = prep_marine_obs.obs_fetch(obsprepSpace, cycles)
        
                        if not matchingFiles:
                            logger.warning("No files found for obs source, skipping")
                            break
        
                        obsprepSpace['input files'] = matchingFiles
                        obsprepSpace['window begin'] = windowBegin
                        obsprepSpace['window end'] = windowEnd
                        outputFilename = f"{RUN}.t{cyc}z.{obs_space_name}.{PDY}{cyc}.nc4"
                        obsprepSpace['output file'] = outputFilename

    @logit(logger)
    def run(self):
        """Method run for ocean obs prep task
        Parameters:
        ------------
        None
        Returns:
        --------
        None
        """

        logger.info("run")

        chdir(self.runtime_config.DATA)

    @logit(logger)
    def finalize(self):
        """Method finalize for ocean obs prep task
        Parameters:
        ------------
        None
        Returns:
        --------
        None
        """

        logger.info("finalize")

        RUN = self.runtime_config.RUN
        cyc = self.runtime_config.cyc
