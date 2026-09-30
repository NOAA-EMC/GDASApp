#!/usr/bin/env python3

import argparse
from datetime import datetime
from varGDAS import varGDAS
from logging import getLogger

logger = getLogger(__name__.split('.')[-1])

parser = argparse.ArgumentParser()
parser.add_argument('--MACHINE_ID', required=True, help='Machine identifier (Ursa, Hercules, etc)')
parser.add_argument('--HOMEgdas', required=True, help='Home directory for GDASApp')
parser.add_argument('--DATA', required=True, help='Run directory')
args = parser.parse_args()

config = {'PDY':        datetime(2021, 3, 23),
          'cyc':        18,
          'assim_freq': 6,
          'MACHINE_ID': args.MACHINE_ID,
          'HOMEgdas':   args.HOMEgdas,
          'DATA':       args.DATA}

var = varGDAS(config)
logger.info("Starting initialize()")
var.initialize()
logger.info("Starting execute('3dvar')")
var.execute('3dvar')
logger.info("Finished execute('3dvar')")
