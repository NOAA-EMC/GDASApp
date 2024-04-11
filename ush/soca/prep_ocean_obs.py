#!/usr/bin/env python3

from datetime import datetime, timedelta
#import f90nml
from logging import getLogger
from multiprocessing import Process
import os
#from soca import bkg_utils
from soca import prep_marine_obs
from typing import Dict
import ufsda
from ufsda.stage import soca_fix
from wxflow import (AttrDict,
                    chdir,
                    Executable,
                    FileHandler,
                    logit,
                    parse_j2yaml,
                    save_as_yaml,
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

        DATA = self.runtime_config.DATA

        # Set the window times
        PDY = self.runtime_config['PDY']
        cyc = self.runtime_config['cyc']
        cdate = PDY + timedelta(hours=cyc)

        self.runtime_config['cdate'] = cdate
        windowBeginDatetime = cdate - timedelta(hours=3)
        windowEndDatetime = cdate + timedelta(hours=3)
        self.windowBegin = windowBeginDatetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.windowEnd = windowEndDatetime.strftime('%Y-%m-%dT%H:%M:%SZ')

        self.config.conversionListFile = 'conversionList.yaml'

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
        cdatestr = cdate.strftime('%Y%m%d%H')
        RUN = self.runtime_config.RUN
        cyc = self.runtime_config['cyc']

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
                        obsprepSpace['window begin'] = self.windowBegin
                        obsprepSpace['window end'] = self.windowEnd
                        outputFilename = f"{RUN}.t{cyc}z.{obs_space_name}.{cdatestr}.nc4"
                        obsprepSpace['output file'] = outputFilename

                        if obsprepSpace['type'] == 'bufr':
                       #     bufr2ioda(obsprepSpaceName, PDY, cyc, RUN, COMIN_OBS, COMIN_OBS)
                       #     files_to_save.append([obsprepSpace['output file'],
                       #                           os.path.join(COMOUT_OBS, obsprepSpace['output file'])])
                            pass
                        else:
                            iodaYamlFilename = obsprepSpaceName + '2ioda.yaml'
                            obsprepSpace['conversion config file'] = iodaYamlFilename
                            save_as_yaml(obsprepSpace, iodaYamlFilename)
                            
#                            files_to_save.append([obsprepSpace['output file'],
#                                                  os.path.join(COMOUT_OBS, obsprepSpace['output file'])])
#                            files_to_save.append([iodaYamlFilename,
#                                                  os.path.join(COMOUT_OBS, iodaYamlFilename)])
        
                            #obsspaces_to_convert.append({"obs space" : {"name" : obs_space_name}})
                            obsspaces_to_convert.append({"obs space": obsprepSpace})


        except TypeError:
            logger.critical("Ill-formed OBS_YAML or OBSPREP_YAML file, exiting")
            raise

        save_as_yaml({"observations" : obsspaces_to_convert}, self.config.conversionListFile )
         
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

        obsspaces_to_convert = YAMLFile(self.config.conversionListFile)

        processes = []
        for obs_to_convert in obsspaces_to_convert['observations']:

            obsspace = obs_to_convert['obs space']
            name = obsspace['name']
            logger.info(f"name: {name}")
            process = Process(target=prep_marine_obs.run_netcdf_to_ioda, args=(name,))
            process.start()
            processes.append((process,obsspace))

        completed = []
        # Wait for all processes to finish
        for processtuple in processes:
            process, obsspace = processtuple
            process.join()
            if process.exitcode == 0:
                completed.append({'obs space':obsspace})

        save_as_yaml({"observations" : completed }, "movetorotdir.yaml")

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
        COMOUT_OBS = self.config.COMOUT_OBS

        obsspaces_to_save =  YAMLFile("movetorotdir.yaml")

        for obsspace_to_save in obsspaces_to_save['observations']:

            obsspace = obsspace_to_save['obs space']
            output_file = obsspace['output file']
            conv_config_file = obsspace['conversion config file']
            output_file_dest = os.path.join(COMOUT_OBS, output_file)
            conv_config_file_dest = os.path.join(COMOUT_OBS,conv_config_file)

            FileHandler({'copy': [[output_file,output_file_dest]]}).sync()
            FileHandler({'copy': [[conv_config_file,conv_config_file_dest]]}).sync()
