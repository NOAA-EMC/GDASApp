#!/usr/bin/env python3

from wxflow import Logger, parse_j2yaml, cast_strdict_as_dtypedict
from bufr2ioda_ssmis import Bufr2IodaSsmis

# Initialize root logger
logger = Logger('gen_bufr2ioda_json.py', level='INFO', colored_log=True)

bufr_classes = [
    Bufr2IodaSsmis,
]

config = {
    'RUN': 123,
    'current_cycle': '2022010412',
    'DATA': 'abcd',
    'DMPDIR': 'abc',
    'COM_OBS': 'abs',
    'PDY': '20220104',
    'cyc': '12',
}


if __name__ == "__main__":

    for bufr_class in bufr_classes:
        converter = bufr_class(config)
        converter.execute()
        logger.info('--Finished--')


