#!/usr/bin/env python3

import os
from logging import getLogger
from wxflow import Dict, logit, Task, YAMLFile
import ufsda

logger = getLogger(__name__.split('.')[-1])


class MarineRecenter(Task):
    """
    Class for global ocean analysis recentering task
    """


    @logit(logger, name="MarineRecenter")
    def __init__(self, config: Dict) -> None:
    """Constructor for ocean recentering task
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

        # Variables of convenience
	gdas_home = os.path.join(config['HOMEgfs'], 'sorc', 'gdas.cd')
        half_assim_freq = timedelta(hours=int(config['assim_freq'])/2)
        window_middle = datetime.strptime(config['PDY')+config['cyc'], '%Y%m%d%H')
        window_begin = datetime.strptime(config['PDY')+config['cyc'], '%Y%m%d%H') - half_assim_freq
        window_begin_iso = window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')
        window_middle_iso = window_middle.strftime('%Y-%m-%dT%H:%M:%SZ')
        fcst_begin = datetime.strptime(config['PDY')+config['cyc'), '%Y%m%d%H')

        self.window_config = {'window_begin': f"{window_begin.strftime('%Y-%m-%dT%H:%M:%SZ')}",
             'ATM_WINDOW_BEGIN': window_begin_iso,
             'ATM_WINDOW_MIDDLE': window_middle_iso,
             'ATM_WINDOW_LENGTH': f"PT{config['assim_freq')}H"}

        _stage_cfg = YAMLFile(path=os.path.join(gdas_home, 'parm', 'templates', 'stage.yaml'))
        _stage_cfg = Template.substitute_structure(_stage_cfg, TemplateConstants.DOUBLE_CURLY_BRACES, self.window_config.get)
        _stage_cfg = Template.substitute_structure(_stage_cfg, TemplateConstants.DOLLAR_PARENTHESES, self.window_config.get)
        self.stage_cfg = _stage_cfg


    @logit(logger)
    def initialize(self):
    """Method initialize for ocean recentering task
    Parameters:
    ------------
    None 
    Returns:
    --------
    None 
    """

        logger.info("initialize")

        ufsda.stage.soca_fix(self.stage_cfg)


    @logit(logger)
    def run(self):
    """Method run for ocean recentering task
    Parameters:
    ------------
    None 
    Returns:
    --------
    None 
    """

        logger.info("run")

    @logit(logger)
    def finalize(self):
    """Method finalize for ocean recentering task
    Parameters:
    ------------
    None 
    Returns:
    --------
    None 
    """

        logger.info("finalize")
