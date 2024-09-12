import sys
import numpy as np
import numpy.ma as ma
import os
import time
from datetime import datetime
from pyiodaconv import bufr
from collections import namedtuple
from pyioda import ioda_obs_space as ioda_ospace
from .util import ParseArguments, run_diff
from .bufr2ioda_config import Bufr2iodaConfig
import logging
import tempfile


# the converter takes a configuration class as input,
# creates the logger and provides a method to run the converter
# and to test the result
# for testing purposes a temporary file is written by the logger
# and it is compared to a reference file
# the logger provides simple human readable numbers,
# as well as cryptographic hashes generated from input
# the hashes are deterministic, yet they are supposedly capable
# of detecting an error with high probability

class Bufr2ioda_Converter:
    def __init__(self, bufr2ioda_config, ioda_vars, logfile):
        ioda_vars.SetOceanBasinNCFilePath(bufr2ioda_config.OceanBasinNCFilePath())
        self.bufr2ioda_config = bufr2ioda_config
        self.ioda_vars = ioda_vars
        self.logfile = logfile
        self.SetupLogging(bufr2ioda_config.script_name, self.logfile)

    def SetupLogging(self, script_name, logfile):
        self.logger = logging.getLogger(script_name)
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        console_handler = logging.StreamHandler()
        # console_handler.setLevel(logging.INFO)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)

        if (logfile):
            self.file_handler = logging.FileHandler(logfile)
            self.file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter('%(message)s')
            self.file_handler.setFormatter(file_formatter)

    def run(self):
        start_time = time.time()

        self.logger.debug(f"BuildQuery")
        q = self.ioda_vars.BuildQuery()

        bufrfile_path = self.bufr2ioda_config.BufrFilepath()
        self.logger.debug(f"ExecuteQuery: BUFR file = {bufrfile_path}")
        with bufr.File(bufrfile_path) as f:
            r = f.execute(q)

        # process query results and set ioda variables
        self.ioda_vars.SetFromQueryResult(r)

        self.ioda_vars.filter()

        # set seqNum, PreQC, ObsError, OceanBasin
        self.ioda_vars.additional_vars.construct()

        iodafile_path = self.bufr2ioda_config.IODAFilepath()
        path, fname = os.path.split(iodafile_path)
        os.makedirs(path, exist_ok=True)

        metadata = self.ioda_vars.metadata

        dims = {'Location': np.arange(0, metadata.lat.shape[0])}
        obsspace = ioda_ospace.ObsSpace(iodafile_path, mode='w', dim_dict=dims)
        self.logger.debug(f"Created IODA file: {iodafile_path}")

        date_range = [str(metadata.dateTime.min()), str(metadata.dateTime.max())]
        self.logger.debug(f"CreateGlobalAttributes")
        self.bufr2ioda_config.CreateIODAAttributes(obsspace, date_range)

        self.logger.debug(f"ioda_vars.WriteToIodaFile")
        self.ioda_vars.WriteToIodaFile(obsspace)

        if (self.logfile):
            self.logger.addHandler(self.file_handler)
        self.ioda_vars.log(self.logger)
        if (self.logfile):
            self.logger.removeHandler(self.file_handler)

        end_time = time.time()
        running_time = end_time - start_time
        self.logger.debug(f"Total running time: {running_time} seconds")

    def test(self, test_file):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as temp_log_file:
            temp_log_file_name = temp_log_file.name
            file_handler = logging.FileHandler(temp_log_file_name)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter('%(message)s')
            file_handler.setFormatter(file_formatter)

            self.logger.debug(f"TEST: created a temporary log file {temp_log_file_name}")
            self.logger.debug(f"TEST: running diff with reference file {test_file}")
            self.logger.addHandler(file_handler)

            self.ioda_vars.log(self.logger)

            result = run_diff(temp_log_file_name, test_file, self.logger)
            if result:
                self.logger.error(f"TEST ERROR: files are different")
            else:
                self.logger.info(f"TEST passed: files are identical")

            return result
