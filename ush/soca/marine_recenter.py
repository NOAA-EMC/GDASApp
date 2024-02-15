#!/usr/bin/env python3

import os
from logging import getLogger
from typing import Dict, List, Any
from wxflow import AttrDict, FileHandler, logit, Task

logger = getLogger(__name__.split('.')[-1])


class MarineRecenter(Task):

    @logit(logger, name="MarineRecenter")
    def __init__(self, config):
        logger.info("init")
        super().__init__(config)

        # Create a local dictionary that is repeatedly used across this class
        local_dict = AttrDict(
            {
                "diags": os.path.join(self.runtime_config['DATA'], 'diags'),            # output dir for soca DA obs space
                "obs_in": os.path.join(self.runtime_config['DATA'], 'obs') ,            # input      "           "
                "bkg_dir": os.path.join(self.runtime_config['DATA'], 'bkg'),            # ice and ocean backgrounds
                "anl_out": os.path.join(self.runtime_config['DATA'], 'Data'),           # output dir for soca DA
                "static_ens": os.path.join(self.runtime_config['DATA'], 'static_ens')  # clim. ens.
            }
        )

        # task_config is everything that this task should need
        self.task_config = AttrDict(**self.config, **self.runtime_config, **local_dict)

        #_soca_ensb_yaml_temp 
        print(self.task_config) 

    @logit(logger)
    def initialize(self):
        logger.info("initialize")

        FileHandler({'mkdir': [self.task_config.diags,
                               self.task_config.obs_in,
                               self.task_config.bkg_dir,
                               self.task_config.anl_out,
                               self.task_config.static_ens]}).sync()



    @logit(logger)
    def run(self):
        logger.info("run")

    @logit(logger)
    def finalize(self):
        logger.info("finalize")
