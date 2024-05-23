#!/usr/bin/env python3

import argparse
import json
import os
from combine_base import Bufr2IodaBase
# from wxflow import Logger
from logging import Logger

logger = Logger(os.path.basename(__file__), level='INFO')


class Bufr2IodaSsmis(Bufr2IodaBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose', help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()
    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger(os.path.basename(__file__), level=log_level)
    converter = Bufr2IodaSsmis(args.config)
    converter.execute()
    logger.info('--Finished--')


