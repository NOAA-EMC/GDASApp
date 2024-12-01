#!/usr/bin/env python3

import sys
from b2ibase.util import parse_arguments
from b2ibase.config import Config
from b2ibase.data_variable_dictionary import DataVariableDictionary
from b2ibase.b2i import B2I 
from b2ibase.log import B2ILogger


# platform_description = 'Surface obs from ALTKOB: temperature and salinity'


class AltkobConfig(Bufr2iodaConfig):
    def ioda_filename(self):
        return f"{self.cycle_type}.t{self.hh}z.insitu_surface_{self.data_format}.{self.cycle_datetime}.nc4"



class AltkobData(DataVariableDictionary):
    def read_from_bufr(self, bufr_file_path):
        super().read_from_bufr(bufr_file_path)
        temp = self.get("seaSurfaceTemperature")
        saln = self.get("salinity")
        mask = temp.get_filter() & saln.get_filter()
        self.filter(mask)


if __name__ == '__main__':

    script_name, config_file, log_file, test_file = parse_arguments()
    var_yaml_file = "altkob.yaml"

    b2i = B2I(AltkobConfig,
        script_name, config_file, platform_description,
        AltkobData)

    b2i.run()
