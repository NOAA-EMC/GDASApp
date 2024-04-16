#!/usr/bin/env python3

from datetime import datetime, timedelta
from gen_bufr2ioda_json import gen_bufr_json
from logging import getLogger
from multiprocessing import Process, Queue
import os
from soca import prep_ocean_obs_utils
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

        PDY = self.runtime_config['PDY']
        cyc = self.runtime_config['cyc']
        cdate = PDY + timedelta(hours=cyc)

        self.runtime_config['cdate'] = cdate
        window_begin_datetime = cdate - timedelta(hours=3)
        window_begin_datetime = cdate + timedelta(hours=3)
        self.window_begin = window_begin_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.window_end = window_begin_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')

        self.config.conversion_list_file = 'conversion_list.yaml'

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
        observer_config = YAMLFile(OBS_YAML)

        OBSPREP_YAML = self.config['OBSPREP_YAML']
        if os.path.exists(OBSPREP_YAML):
            obsprep_config = YAMLFile(OBSPREP_YAML)
        else:
            logger.critical(f"OBSPREP_YAML file {OBSPREP_YAML} does not exist")
            raise FileNotFoundError

        JSON_TMPL_DIR = self.config.JSON_TMPL_DIR
        BUFR2IODA_PY_DIR = self.config.BUFR2IODA_PY_DIR

        COMIN_OBS = self.config.COMIN_OBS
        COMOUT_OBS = self.config['COMOUT_OBS']
        if not os.path.exists(COMOUT_OBS):
            os.makedirs(COMOUT_OBS)
    
        files_to_save = []
        obsspaces_to_convert = []
        
        try:
            # go through the sources in OBS_YAML
            for observer in observer_config['observers']:
                try:
                    obs_space_name = observer['obs space']['name']
                    logger.info(f"obs_space_name: {obs_space_name}")
                except KeyError:
                    logger.warning("Ill-formed observer yaml file, skipping")
                    continue
        
                # find match to the obs space from OBS_YAML in OBSPREP_YAML
                # this is awkward and unpythonic, so feel free to improve
                for observation in obsprep_config['observers']:
                    obsprepSpace = observation['obs space']
                    obsprepSpaceName = obsprepSpace['name']
        
                    if obsprepSpaceName == obs_space_name:
                        obtype = obsprepSpaceName # for clarity
                        logger.info(f"obtype: {obs_space_name}")
        
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
        
                        matchingFiles = prep_ocean_obs_utils.obs_fetch(obsprepSpace, cycles)
        
                        if not matchingFiles:
                            logger.warning(f"No files found for obs source {obtype}, skipping")
                            break
        
                        obsprepSpace['input files'] = matchingFiles
                        obsprepSpace['window begin'] = self.window_begin
                        obsprepSpace['window end'] = self.window_end
                        outputFilename = f"{RUN}.t{cyc}z.{obs_space_name}.{cdatestr}.nc4"
                        obsprepSpace['output file'] = outputFilename

                        if obsprepSpace['type'] == 'bufr':
                            gen_bufr_json_config =  {
                                                     'RUN': RUN,
                                                     'current_cycle': cdate,
                                                     'DMPDIR': COMIN_OBS,
                                                     'COM_OBS': COMIN_OBS,
                                                     }
                            json_config_file = os.path.join(COMIN_OBS,
                                    f"{obtype}_{cdatestr}.json")
                            obsprepSpace['conversion config file'] = json_config_file
                            bufr2iodapy = BUFR2IODA_PY_DIR + '/bufr2ioda_' + obtype + '.py'
                            obsprepSpace['bufr2ioda converter'] = bufr2iodapy
                            tmpl_filename = 'bufr2ioda_' + obtype + '.json'
                            template = os.path.join(JSON_TMPL_DIR, tmpl_filename)
                            try:
                                gen_bufr_json(gen_bufr_json_config, template, json_config_file)
                            except Exception as e:
                                logger.warning(f"An exeception {e} occured while trying to run gen_bufr_json")
                                logger.warning(f"obtype {obtype} will be skipped")
                                continue # to next obtype

                            obsspaces_to_convert.append({"obs space": obsprepSpace})

                        elif obsprepSpace['type'] == 'nc':
                            iodaYamlFilename = obtype + '2ioda.yaml'
                            obsprepSpace['conversion config file'] = iodaYamlFilename
                            save_as_yaml(obsprepSpace, iodaYamlFilename)

                            obsspaces_to_convert.append({"obs space": obsprepSpace})

                        else:
                            logger.warning(f"obs space {obtype} has bad type {obsprepSpace['type']}, skipping")
                            


        except TypeError:
            logger.critical("Ill-formed OBS_YAML or OBSPREP_YAML file, exiting")
            raise

        # yes, there is redundancy between the yamls fed to the ioda converter and here,
        # this seems safer and easier than being selective about the fields
        save_as_yaml({"observers" : obsspaces_to_convert}, self.config.conversion_list_file )
         
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

        obsspaces_to_convert = YAMLFile(self.config.conversion_list_file)

        processes = []
        for obs_to_convert in obsspaces_to_convert['observers']:

            obsspace = obs_to_convert['obs space']
            obtype = obsspace['name']
            logger.info(f"name: {obtype}")
            if obsspace["type"] == "nc":
                process = Process(target=prep_ocean_obs_utils.run_netcdf_to_ioda, args=(obsspace,))
            elif obsspace["type"] == "bufr":
                process = Process(target=prep_ocean_obs_utils.run_bufr_to_ioda, args=(obsspace,))
            else:
                logger.warning(f"Invalid observation format {obsspace['type']}, skipping obtype {obtype}")
                continue
            process.start()
            processes.append((process,obsspace))

        completed = []
        # Wait for all processes to finish
        # TODO(AFE): add return value checking
        for process, obsspace in processes:
            process.join()
            completed.append(obsspace)

        save_as_yaml({"observers" : completed }, "movetorotdir.yaml")

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

        for obsspace_to_save in obsspaces_to_save['observers']:

            #obsspace = obsspace_to_save['obs space']
            #output_file = obsspace['output file']
            output_file = obsspace_to_save['output file']
            #conv_config_file = obsspace['conversion config file']
            conv_config_file = obsspace_to_save['conversion config file']
            output_file_dest = os.path.join(COMOUT_OBS, output_file)
            conv_config_file_dest = os.path.join(COMOUT_OBS,conv_config_file)

            try:
                FileHandler({'copy': [[output_file,output_file_dest]]}).sync()
                FileHandler({'copy': [[conv_config_file,conv_config_file_dest]]}).sync()
            except OSError:
                logger.warning(f"Obs file not found, possible IODA converter failure)")
                continue
