#!/usr/bin/env python3

from datetime import datetime, timedelta
from gen_bufr2ioda_json import gen_bufr_json
from logging import getLogger
from multiprocessing import Process
import os
import glob
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
        window_end_datetime = cdate + timedelta(hours=half_assim_freq)
        self.window_begin = window_begin_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.window_end = window_end_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')

        self.task_config.conversion_list_file = 'conversion_list.yaml'
        self.task_config.save_list_file = 'save_list.yaml'
        self.task_config.app_path_observations = self.task_config['MARINE_JCB_GDAS_OBS']

    """
    Copies observation files from the OBSFORGE_OBS_DB directory to the
    destination directory specified in the task configuration.

    Args:
        dmpdir (str): The directory path where observation files are located.

    Functionality:
        - Iterates over predefined observation types
          ('adt', 'icec', 'sst', 'sss').
        - Searches for NetCDF files (*.nc) in the specified directory
          structure based on the task configuration.
        - Logs the number of files found for each observation type and
          the copying process.
        - Constructs the destination file path using the `COMOUT_OBS`
          directory from the task configuration.
        - Uses the `FileHandler` class to synchronize (copy) the files from
          the source to the destination.

    Logging:
        - Logs the number of files found for each observation type.
        - Logs the source file being copied.

    Raises:
        - Any exceptions raised by `glob.glob` or `FileHandler.sync()` will
          propagate to the caller.

    Notes:
        - The method assumes that the `task_config` dictionary contains
          keys 'RUN', 'PDY', 'cyc', and 'COMOUT_OBS'.
        - The `PDY` key is expected to be a datetime object.
    """
    @logit(logger)
    def copy_from_obsforge(self):
        obsfiles_src_dst = []
        dmpdir = self.task_config['DMPDIR']
        comout_obs = self.task_config['COMOUT_OBS']
        run_date = self.task_config['PDY'].strftime('%Y%m%d')
        cycle = str(self.task_config['cyc']).zfill(2)  # ensures '00', '06', etc.
        run = self.task_config['RUN']

        # Ensure output directory exists
        os.makedirs(comout_obs, exist_ok=True)

        obs_types = ['adt', 'icec', 'sst', 'sss', 'insitu']

        # Loop through the observation types
        for obs_type in obs_types:

            # Skip ADT obs if cycle is not 00Z
            if obs_type == 'adt' and cycle != '00':
                logger.info(f"***** Skipping {obs_type} for cycle {cycle}")
                continue

            search_path = os.path.join(dmpdir, f"{run}.{run_date}", cycle, 'ocean', obs_type, '*.nc')
            src_files = glob.glob(search_path)
            logger.info(f"***** Found {len(src_files)} files for {obs_type} in {dmpdir}")

            # Loop through the source files and prepare them for copying
            for src_file in src_files:
                dst_file = os.path.join(comout_obs, os.path.basename(src_file))
                logger.info(f"***** Copying {src_file} to {dst_file}")
                obsfiles_src_dst.append([src_file, dst_file])

        if obsfiles_src_dst:
            FileHandler({'copy': obsfiles_src_dst}).sync()
        else:
            logger.warning("***** No files found to copy.")

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

        OBS_YAML = self.task_config['OBS_LIST_YAML']
        self.task_config.observations = parse_j2yaml(OBS_YAML, self.task_config)['observations']

        obsconfigfile = os.path.join(self.task_config['PARMgfs'], 'gdas/marine/obs/obs_list_base.yaml.j2')
        obsconfig = parse_j2yaml(obsconfigfile, self.task_config)['observers']

        OBSPREP_YAML = self.task_config['OBSPREP_YAML']
        if os.path.exists(OBSPREP_YAML):
            obsprep_config = YAMLFile(OBSPREP_YAML)
        else:
            logger.critical(f"OBSPREP_YAML file {OBSPREP_YAML} does not exist")
            raise FileNotFoundError

        # TODO (AFE): this should be in the task config file in g-w
        BUFR2IODA_TMPL_DIR = os.path.join(self.task_config.HOMEgfs, 'parm/gdas/ioda/bufr2ioda')
        # TODO (AFE): this should be in the task config file in g-w, and reaches into GDASApp
        # in order to avoid touching the g-w until we know this will remain a task
        BUFR2IODA_PY_DIR = os.path.join(self.task_config.HOMEgfs, 'sorc/gdas.cd/ush/ioda/bufr2ioda/marine/b2i')

        DATA = self.task_config.DATA
        COMOUT_OBS = self.task_config['COMOUT_OBS']
        OCEAN_BASIN_FILE = self.task_config['OCEAN_BASIN_FILE']
        if not os.path.exists(COMOUT_OBS):
            os.makedirs(COMOUT_OBS)

        obsspaces_to_convert = []

        try:
            # go through the sources in OBS_YAML
            for observation in obsconfig:
                obs_space = observation['obs space']
                obs_space_name = obs_space['name']

                # find match to the obs space from OBS_YAML in OBSPREP_YAML
                # this is awkward and unpythonic, so feel free to improve
                for obsprep_entry in obsprep_config['observations']:
                    obsprep_space = obsprep_entry['obs space']  # the whole thing is needed later
                    obsprep_space_name = obsprep_space['name']
                    if obsprep_space_name == obs_space_name:
                        logger.info(f"Observer {obs_space_name} found in OBSPREP_YAML")

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

                        # fetch the obs files to DATA directory and get the list of files and cycles
                        fetched_files = prep_ocean_obs_utils.obs_fetch(self.task_config,
                                                                       self.task_config,
                                                                       obsprep_space,
                                                                       window_cdates)

                        if not fetched_files:
                            logger.warning(f"No files found for obs source {obs_space_name}, skipping")
                            break  # go to next obs_space_name in OBS_YAML

                        obsprep_space['window begin'] = self.window_begin
                        obsprep_space['window end'] = self.window_end
                        ioda_config_file = obs_space_name + '2ioda.yaml'
                        obsprep_space['conversion config file'] = ioda_config_file

                        # set up the config file for conversion to IODA for bufr and
                        # netcdf files respectively
                        if obsprep_space['type'] == 'bufr':

                            # create a pre-filled template file for the bufr2ioda converter,
                            # which will be overwritten for each input cycle
                            bufrconv_config = {
                                'RUN': RUN,
                                'current_cycle': cdate,
                                'DMPDIR': DATA,
                                'COMOUT_OBS': DATA,
                                'OCEAN_BASIN_FILE': OCEAN_BASIN_FILE}
                            bufr2iodapy = os.path.join(BUFR2IODA_PY_DIR, f'bufr2ioda_{obs_space_name}.py')
                            obsprep_space['bufr2ioda converter'] = bufr2iodapy
                            tmpl_filename = f"bufr2ioda_{obs_space_name}.yaml"
                            bufrconv_template = os.path.join(BUFR2IODA_TMPL_DIR, tmpl_filename)
                            input_files = []  # files to save to COM directory
                            bufrconv_files = []  # files needed to populate the IODA converter config

                            # for each cycle of the retrieved obs bufr files...
                            for input_file, cycle in fetched_files:
                                cycletime = cycle[8:10]
                                ioda_filename = f"{RUN}.t{cycletime}z.{obs_space_name}.{cycle}.nc4"
                                bufrconv_files.append((cycle, input_file, ioda_filename))
                                input_files.append(ioda_filename)

                            obsprep_space['bufrconv files'] = bufrconv_files
                            # set up config for concatenation
                            concat_config = {
                                'provider': 'INSITUOBS',
                                'window begin': obsprep_space['window begin'],
                                'window end': obsprep_space['window end'],
                                'variable': obs_space['observed variables'][0],
                                'error ratio': obsprep_space['error ratio'],
                                'input files': input_files,
                                'output file': f"{RUN}.t{cycletime}z.{obs_space_name}.{cdatestr}.nc4"
                            }
                            concat_config_file = obs_space_name + '_concat.yaml'

                            obsprep_space['output file'] = concat_config['output file']

                            try:
                                bufrconv = parse_j2yaml(bufrconv_template, bufrconv_config)
                                bufrconv.update(obsprep_space)
                                bufrconv.save(ioda_config_file)
                                save_as_yaml(concat_config, concat_config_file)
                            except Exception as e:
                                logger.warning(f"An exeception {e} occured while trying to create BUFR2IODA config")
                                logger.warning(f"obs_space_name {obs_space_name} will be skipped")
                                break  # go to next observer in OBS_YAML

                            obsspaces_to_convert.append({"obs space": obsprep_space})

                        elif obsprep_space['type'] == 'nc':

                            obsprep_space['input files'] = [f[0] for f in fetched_files]
                            ioda_filename = f"{RUN}.t{cyc:02d}z.{obs_space_name}.{cdatestr}.nc4"
                            obsprep_space['output file'] = ioda_filename
                            save_as_yaml(obsprep_space, ioda_config_file)

                            obsspaces_to_convert.append({"obs space": obsprep_space})

                        else:
                            logger.warning(f"obs space {obs_space_name} has bad type {obsprep_space['type']}, skipping")

        except TypeError:
            logger.critical("Ill-formed OBS_YAML or OBSPREP_YAML file, exiting")
            raise

        # yes, there is redundancy between the yamls fed to the ioda converters and here,
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
            obs_space_name = obs_space['name']
            logger.info(f"Trying to convert {obs_space_name} to IODA")
            if obs_space["type"] == "nc":
                process = Process(target=prep_ocean_obs_utils.run_netcdf_to_ioda, args=(obs_space,
                                                                                        self.task_config.OCNOBS2IODAEXEC))
            elif obs_space["type"] == "bufr":
                process = Process(target=prep_ocean_obs_utils.run_bufr_to_ioda, args=(obs_space, self.task_config.OCNOBS2IODAEXEC))
            else:
                logger.warning(f"Invalid observation format {obs_space['type']}, skipping obs_space_name {obs_space_name}")
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
        files_to_save = []

        for obs_space in obsspaces_to_save['observations']:

            conv_config_file = os.path.basename(obs_space['conversion config file'])
            if os.path.exists(conv_config_file):
                conv_config_file_dest = os.path.join(COMOUT_OBS, conv_config_file)
                files_to_save.append([conv_config_file, conv_config_file_dest])
            else:
                logger.warning(f"IODA conversion config file {conv_config_file} does not exist, cannot copy to COMROOT")

            ioda_file = os.path.basename(obs_space['output file'])
            if os.path.exists(ioda_file):
                obs_file_dest = os.path.join(COMOUT_OBS, ioda_file)
                files_to_save.append([ioda_file, obs_file_dest])
            else:
                logger.warning(f"IODA file {ioda_file} does not exist, cannot copy to COMROOT")

        FileHandler({'copy': files_to_save}).sync()
