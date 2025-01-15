import os
import sys
import numpy as np
import numpy.ma as ma
import math
import netCDF4 as nc
import xarray as xr

# OceanBasin class provides a facility to add an OceanBasin
# metadata variable using lon and lat
# basic definition of ocean basins is read from an nc file,
# We search for the filename, depending on the system
# The path to the ocean basin nc file can be supplied
# in the implementation of the converter

# the main method is get_station_basin which returns the ocean basin
# for a list of station coordinates


class OceanBasin:
    def __init__(self, ocean_basin_nc_file_path):
        self.read_nc_file(ocean_basin_nc_file_path)

    def read_nc_file(self, ocean_basin_nc_file_path):
        try:
            with nc.Dataset(ocean_basin_nc_file_path, 'r') as nc_file:
                variable_name = 'open_ocean'
                if variable_name in nc_file.variables:
                    lat_dim = nc_file.dimensions['lat'].size
                    lon_dim = nc_file.dimensions['lon'].size
                    self.__latitudes = nc_file.variables['lat'][:]
                    self.__longitudes = nc_file.variables['lon'][:]

                    variable = nc_file.variables[variable_name]
                    # Read the variable data into a numpy array
                    variable_data = variable[:]
                    # Convert to 2D numpy array
                    self.__basin_array = np.reshape(variable_data, (lat_dim, lon_dim))
        except FileNotFoundError:
            print(f"The file {file_path} does not exist.")
            sys.exit(1)
        except IOError as e:
            # Handle other I/O errors, such as permission errors
            print(f"An IOError occurred: {e}")
            sys.exit(1)

    # input: 2 vectors of station coordinates
    # output: a vector of station ocean basin values
    def get_station_basin(self, lat, lon):
        n = len(lon)

        lat0 = self.__latitudes[0]
        dlat = self.__latitudes[1] - self.__latitudes[0]
        lon0 = self.__longitudes[0]
        dlon = self.__longitudes[1] - self.__longitudes[0]

        # the data may be a masked array
        ocean_basin = []
        for i in range(n):
            if not ma.is_masked(lat[i]):
                i1 = round((lat[i] - lat0) / dlat)
                i2 = round((lon[i] - lon0) / dlon)
                ocean_basin.append(self.__basin_array[i1][i2])
        return np.array(ocean_basin, dtype=np.int32)
