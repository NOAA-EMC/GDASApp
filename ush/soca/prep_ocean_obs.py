#!/usr/bin/env python3

from datetime import datetime, timedelta
from gen_bufr2ioda_json import gen_bufr_json
from logging import getLogger
from multiprocessing import Process
import os
from soca import prep_ocean_obs_utils
from typing import Dict
from wxflow import (chdir,
                    FileHandler,
                    logit,
                    parse_j2yaml,
                    save_as_yaml,
                    Task,
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
            configuration, namely environment variables
        Returns:
        --------
        None
        """

        logger.info("init")
        super().__init__(config)

        PDY = self.task_config['PDY']
        cyc = self.task_config['cyc']
        cdate = PDY + timedelta(hours=cyc)
        assim_freq = self.task_config['assim_freq']
        half_assim_freq = assim_freq/2

        self.task_config['cdate'] = cdate
        window_begin_datetime = cdate - timedelta(hours=half_assim_freq)
        window_begin_datetime = cdate + timedelta(hours=half_assim_freq)
        self.window_begin = window_begin_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.window_end = window_begin_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')

        self.task_config.conversion_list_file = 'conversion_list.yaml'
        self.task_config.save_list_file = 'save_list.yaml'

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

        cdate = self.task_config['cdate']
        cdatestr = cdate.strftime('%Y%m%d%H')
        RUN = self.task_config.RUN
        cyc = self.task_config['cyc']
        assim_freq = self.task_config['assim_freq']

        SOCA_INPUT_FIX_DIR = self.task_config['SOCA_INPUT_FIX_DIR']
        ocean_mask_src = os.path.join(SOCA_INPUT_FIX_DIR, 'RECCAP2_region_masks_all_v20221025.nc')
        ocean_mask_dest = os.path.join(self.task_config.DATA, 'RECCAP2_region_masks_all_v20221025.nc')
        self.task_config['OCEAN_BASIN_FILE'] = ocean_mask_dest

        try:
            FileHandler({'copy': [[ocean_mask_src, ocean_mask_dest]]}).sync()
        except OSError:
            logger.warning("Could not copy RECCAP2_region_masks_all_v20221025.nc")

        OBS_YAML = self.task_config['OBS_YAML']
        observer_config = YAMLFile(OBS_YAML)

        OBSPREP_YAML = self.task_config['OBSPREP_YAML']
        if os.path.exists(OBSPREP_YAML):
            obsprep_config = YAMLFile(OBSPREP_YAML)
        else:
            logger.critical(f"OBSPREP_YAML file {OBSPREP_YAML} does not exist")
            raise FileNotFoundError

        JSON_TMPL_DIR = self.task_config.JSON_TMPL_DIR
#        BUFR2IODA_PY_DIR = self.task_config.BUFR2IODA_PY_DIR
        BUFR2IODA_PY_DIR = os.path.join(self.task_config.HOMEgfs, 'sorc/gdas.cd/ush/ioda/bufr2ioda/marine/b2i')

        COMIN_OBS = self.task_config.COMIN_OBS
        COMOUT_OBS = self.task_config['COMOUT_OBS']
        OCEAN_BASIN_FILE = self.task_config['OCEAN_BASIN_FILE']
        if not os.path.exists(COMOUT_OBS):
            os.makedirs(COMOUT_OBS)

        obsspaces_to_convert = []

        try:
            # go through the sources in OBS_YAML
            for observer in observer_config['observers']:
                try:
                    obs_space_name = observer['obs space']['name']
                    logger.info(f"Trying to find observation {obs_space_name} in OBSPREP_YAML")
                except KeyError:
                    logger.warning("Ill-formed observer yaml file, skipping")
                    continue

                # find match to the obs space from OBS_YAML in OBSPREP_YAML
                # this is awkward and unpythonic, so feel free to improve
                for obsprep_entry in obsprep_config['observations']:
                    obsprep_space = obsprep_entry['obs space']
                    obsprep_space_name = obsprep_space['name']

                    if obsprep_space_name == obs_space_name:
                        obtype = obsprep_space_name  # for brevity
                        logger.info(f"Observer {obtype} found in OBSPREP_YAML")

                        try:
                            obs_window_back = obsprep_space['window']['back']
                            obs_window_forward = obsprep_space['window']['forward']
                        except KeyError:
                            obs_window_back = 0
                            obs_window_forward = 0

                        window_cdates = []
                        for i in range(-obs_window_back, obs_window_forward + 1):
                            interval = timedelta(hours=assim_freq * i)
                            window_cdates.append(cdate + interval)

                        input_files = prep_ocean_obs_utils.obs_fetch(self.task_config,
                                                                     self.task_config,
                                                                     obsprep_space,
                                                                     window_cdates)

                        if not input_files:
                            logger.warning(f"No files found for obs source {obtype}, skipping")
                            break  # go to next observer in OBS_YAML

                        obsprep_space['input files'] = input_files
                        obsprep_space['window begin'] = self.window_begin
                        obsprep_space['window end'] = self.window_end
                        ioda_filename = f"{RUN}.t{cyc:02d}z.{obs_space_name}.{cdatestr}.nc4"
                        obsprep_space['output file'] = ioda_filename

                        # set up the config file for conversion to IODA for bufr and
                        # netcdf files respectively
                        if obsprep_space['type'] == 'bufr':
                            gen_bufr_yaml_config = {'RUN': RUN,
                                                    'current_cycle': cdate,
                                                    'DMPDIR': COMIN_OBS,
                                                    'COM_OBS': COMIN_OBS,
                                                    'OCEAN_BASIN_FILE': OCEAN_BASIN_FILE}
                            yaml_config_file = os.path.join(COMIN_OBS,
                                                            f"{obtype}_{cdatestr}.yaml")
                            obsprep_space['conversion config file'] = yaml_config_file
                            bufr2iodapy = BUFR2IODA_PY_DIR + '/bufr2ioda_' + obtype + '.py'
                            obsprep_space['bufr2ioda converter'] = bufr2iodapy
                            tmpl_filename = 'bufr2ioda_' + obtype + '.yaml'
                            template = os.path.join(JSON_TMPL_DIR, tmpl_filename)
                            
                            try:
#                                gen_bufr_json(gen_bufr_json_config, template, yaml_config_file)
                                myyaml = parse_j2yaml(template, gen_bufr_yaml_config, yaml_config_file)
                                myyaml.save(yaml_config_file)
                            except Exception as e:
                                logger.warning(f"An exeception {e} occured while trying to run gen_bufr_json")
                                logger.warning(f"obtype {obtype} will be skipped")
                                break  # go to next observer in OBS_YAML

                            obsspaces_to_convert.append({"obs space": obsprep_space})

                        elif obsprep_space['type'] == 'nc':
                            ioda_config_file = obtype + '2ioda.yaml'
                            obsprep_space['conversion config file'] = ioda_config_file
                            save_as_yaml(obsprep_space, ioda_config_file)

                            obsspaces_to_convert.append({"obs space": obsprep_space})

                        else:
                            logger.warning(f"obs space {obtype} has bad type {obsprep_space['type']}, skipping")

        except TypeError:
            logger.critical("Ill-formed OBS_YAML or OBSPREP_YAML file, exiting")
            raise

        # yes, there is redundancy between the yamls fed to the ioda converter and here,
        # this seems safer and easier than being selective about the fields
        save_as_yaml({"observations": obsspaces_to_convert}, self.task_config.conversion_list_file)

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

        chdir(self.task_config.DATA)

        obsspaces_to_convert = YAMLFile(self.task_config.conversion_list_file)

        processes = []
        for observation in obsspaces_to_convert['observations']:

            obs_space = observation['obs space']
            obtype = obs_space['name']
            logger.info(f"Trying to convert {obtype} to IODA")
            if obs_space["type"] == "nc":
                process = Process(target=prep_ocean_obs_utils.run_netcdf_to_ioda, args=(obs_space,
                                                                                        self.task_config.OCNOBS2IODAEXEC))
            elif obs_space["type"] == "bufr":
                process = Process(target=prep_ocean_obs_utils.run_bufr_to_ioda, args=(obs_space,))
            else:
                logger.warning(f"Invalid observation format {obs_space['type']}, skipping obtype {obtype}")
                continue
            process.start()
            processes.append((process, obs_space))

        completed = []
        # Wait for all processes to finish
        # TODO(AFE): add return value checking
        for process, obs_space in processes:
            process.join()
            completed.append(obs_space)

        save_as_yaml({"observations": completed}, self.task_config.save_list_file)

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

        RUN = self.task_config.RUN
        cyc = self.task_config.cyc
        COMOUT_OBS = self.task_config.COMOUT_OBS

        obsspaces_to_save = YAMLFile(self.task_config.save_list_file)

        for obsspace_to_save in obsspaces_to_save['observations']:

            output_file = obsspace_to_save['output file']
            conv_config_file = obsspace_to_save['conversion config file']
            output_file_dest = os.path.join(COMOUT_OBS, output_file)
            conv_config_file_dest = os.path.join(COMOUT_OBS, conv_config_file)

            try:
                FileHandler({'copy': [[output_file, output_file_dest]]}).sync()
                FileHandler({'copy': [[conv_config_file, conv_config_file_dest]]}).sync()
            except OSError:
                logger.warning(f"Obs file not found, possible IODA converter failure)")
                continue
