import numpy as np
import yaml
from pyioda import ioda_obs_space as ioda_ospace
from .data_set import DataSet
from .data_variable import DataVariable
from .variables import *


# adding a dictionary to the data set
class DataVariableDictionary(DataSet):
    def __init__(self, logger):
        self.logger = logger
        super().__init__(logger)
        self._variable_dict = {}

    def add(self, variable: DataVariable):
        # Use the short_name as the key in the dictionary
        if variable._short_name in self._variable_dict:
            self.logger.warning(f"'{variable._short_name}' already exists, overwriting.")
        self._variable_dict[variable._short_name] = variable
        super().add(variable)

    # remove a variable both from the data set and the dictionary
    def remove(self, short_name):
        v = self._variable_dict.pop(short_name, None)  # None is returned if the key is not found
        super().remove(v)

    def get(self, short_name: str):
        # Return the variable associated with the short_name
        return self._variable_dict.get(short_name, None)

    def print_var_list(self):
        for name, value in self._variable_dict.items():
            print(name)

    def __repr__(self):
        return f"DataVariableDictionary({len(self._variable_dict)} variables)"

    def read_from_yaml(self, yaml_file):
        with open(yaml_file, 'r') as file:
            data = yaml.safe_load(file)
        # print("Loaded data from YAML:", data)

        for var_data in data:
            class_name = var_data['class_name']

            # Remove the 'class_name' key from the dictionary to get only the parameters
            parameters = {k: v for k, v in var_data.items() if k != 'class_name'}
            # add this dictionary to the parameter list
            parameters["data_dictionary"] = self

            # Dynamically get the class by name
            variable_class = globals()[class_name]

            if variable_class:
                # Instantiate the class using the unpacked parameters
                instance = variable_class(**parameters)  # Unpack the dictionary into keyword arguments
                self.add(instance)

    def add_preqc_vars(self):
        for v in self.data_variables:
            if v.get_descriptor() == "ObsValue":
                self.add(PreQCVariable(v))
                self.logger.debug(f"added preqc variable for {v.get_name()}")

    def add_error_vars(self):
        for v in self.data_variables:
            if v.get_descriptor() == "ObsValue":
                self.add(ErrorVariable(v))
                self.logger.debug(f"added error variable for {v.get_name()}")

    # needs to have PreQC for correct dtype, fill_value
    def add_seq_num(self):
        # find a preqc variable based on a descriptor
        for v in self.data_variables:
            if v.get_descriptor() == "PreQC":
                preqc = v.get_data()
        dtype = preqc.dtype
        fill_value = preqc.fill_value
        lat = self.get("latitude")
        lon = self.get("longitude")
        seq_num = SequenceNumber(lon.get_data(), lat.get_data(), dtype, fill_value)
        self.add(seq_num)
        self.logger.debug("added sequence number variable")

    def add_ocean_basin(self, nc_file_path):
        # find a preqc variable based on a descriptor
        for v in self.data_variables:
            if v.get_descriptor() == "PreQC":
                preqc = v.get_data()
        dtype = preqc.dtype
        fill_value = preqc.fill_value
        lat = self.get("latitude")
        lon = self.get("longitude")
        ocean_basin = OceanBasinVariable(nc_file_path, lon.get_data(), lat.get_data(), dtype, fill_value)
        self.add(ocean_basin)
        self.logger.debug("added ocean basin variable")

    def write_to_ioda_file(self, b2i_config):
        iodafile_path = b2i_config.ioda_filepath()
        path, fname = os.path.split(iodafile_path)
        os.makedirs(path, exist_ok=True)

        n = self.get_data_size()
        dims = {'Location': np.arange(0, n)}
        obsspace = ioda_ospace.ObsSpace(iodafile_path, mode='w', dim_dict=dims)

        date_time = self.get("dateTime")
        min_date = date_time.get_data().min()
        max_date = date_time.get_data().max()
        date_range = [str(min_date), str(max_date)]
        b2i_config.create_ioda_attributes(obsspace, date_range)

        self.create_ioda_objects(obsspace)
        self.logger.debug(f"written ioda variables to {iodafile_path}")
