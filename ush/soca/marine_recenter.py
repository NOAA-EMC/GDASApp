#!/usr/bin/env python3

import os
from logging import getLogger
from typing import Dict, List, Any
from wxflow import logit

logger = getLogger(__name__.split('.')[-1])


class MarineRecenter():

    def __init__(self, config):
        logger.info("init")

    @logit(logger)
    def initialize(self):
        logger.info("initialize")

    @logit(logger)
    def run(self):
        logger.info("run")

    @logit(logger)
    def finalize(self):
        logger.info("finalize")
