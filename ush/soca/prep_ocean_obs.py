#!/usr/bin/env python3

from datetime import datetime, timedelta
from logging import getLogger
import os
import glob
import tempfile
from typing import Dict
from wxflow import (Executable,
                    FileHandler,
                    Jinja,
                    logit,
                    Task)

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
        PARMgfs = self.task_config['PARMgfs']

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
            logger.warning("***** No files found to copy, generating dummy sst obs file.")
            # source is arbitrary sst
            dummy_source = "sst_avhrr_ma_l3u"
            output_nc = f"{run}.t{cycle}z.{dummy_source}.nc"
            # TODO (AFE) replace this with something set in a config file
            dummy_cdl = os.path.join(PARMgfs, 'gdas', 'marine', 'marine_prepobs_dummyobs.cdl')

            converter = Executable('ncgen')
            converter.add_default_arg('-o')
            converter.add_default_arg(output_nc)
            converter.add_default_arg(dummy_cdl)
            try:
               logger.debug(f"Executing {converter}")
               converter()
            except Exception as e:
               logger.warning(f"Execution failed for {converter}: {e}")
               logger.debug("Exception details", exc_info=True)
               exit(1)

            FileHandler({'copy': [[output_nc, os.path.join(comout_obs, output_nc)]] }).sync()
