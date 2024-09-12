#!/usr/bin/env python3

import os
import sys
import numpy as np
import numpy.ma as ma
import math
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import netCDF4 as nc
import xarray as xr

# OceanBasin class provides a facility to add an OceanBasin
# metadata variable using lon and lat
# basic definition of ocean basins is read from an nc file,
# We search for the filename, depending on the system
# The path to the ocean basin nc file can be supplied
# in the implementation of the converter

# the main method is GetStationBasin which returns the ocean basin
# for a list of station coordinates
# there are methods for plotting and printing the ocean basin data
# as well as printing and plotting station basin data


class OceanBasin:
    def __init__(self):
        # self.FindOceanBasinNCFile()
        pass

    def SetOceanBasinNCFilePath(self, filename):
        self.ocean_basin_nc_file_path = filename

    def FindOceanBasinNCFile(self):
        # try on hera:
        trypath = "/scratch2/NCEPDEV/ocean/Guillaume.Vernieres/data/static/common/RECCAP2_region_masks_all_v20221025.nc"
        if os.path.exists(trypath):
            self.ocean_basin_nc_file_path = trypath
        else:
            # try on orion
            trypath = "/work/noaa/global/glopara/fix/gdas/soca/20240802/common/RECCAP2_region_masks_all_v20221025.nc"
            if os.path.exists(trypath):
                self.ocean_basin_nc_file_path = trypath
            else:
                # file not found
                self.ocean_basin_nc_file_path = ""

    def ReadNCFile(self):
        try:
            with nc.Dataset(self.ocean_basin_nc_file_path, 'r') as nc_file:
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

    def PrintBasin(self):
        for i in range(n1):
            for j in range(n2):
                print(i, j, self.__basin_array[i][j])

    def PlotBasin(self):
        # Create a figure and axes with Cartopy projection
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

        # Plot the ocean basins using a colormap with 6 colors
        # cmap = plt.cm.get_cmap('rainbow', 6)  # Choose a colormap with 6 colors
        cmap = plt.get_cmap('viridis', 6)  # Create a colormap with 6 discrete colors
        im = ax.pcolormesh(self.__longitudes, self.__latitudes, self.__basin_array, cmap='viridis', shading='auto', transform=ccrs.PlateCarree())

        # Add colorbar
        cbar = fig.colorbar(im, ax=ax, orientation='vertical', pad=0.05, ticks=np.arange(0, 6))
        cbar.set_label('Ocean Basin', fontsize=12)
        # Add title and gridlines
        ax.set_title('Ocean Basin Map', fontsize=16)
        ax.coastlines()
        ax.gridlines(draw_labels=True)
        # Show the plot
        plt.show()
        plt.savefig('ocean_basin.png', dpi=300)

    # input: 2 vectors of station coordinates
    # output: a vector of station ocean basin values
    def GetStationBasin(self, lat, lon):
        n = len(lon)
        # print("number of stations = ", n)

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
        return ocean_basin

    def PrintStationBasin(self, lon, lat, file_path):
        ocean_basin = self.GetStationBasin(lat, lon)
        with open(file_path, 'w') as file:
            # Iterate over lon, lat, and ocean_basin arrays simultaneously
            for lat_val, lon_val, basin_val in zip(lat, lon, ocean_basin):
                file.write(f"{lat_val} {lon_val} {basin_val}\n")

    def PlotStations(self, lon, lat, png_file):
        ocean_basin = self.GetStationBasin(lon, lat)

        # Initialize the plot
        plt.figure(figsize=(12, 8))
        # Create a Cartopy map with PlateCarree projection (latitude/longitude)
        ax = plt.axes(projection=ccrs.PlateCarree())
        # Add coastlines and borders
        ax.coastlines()
        ax.add_feature(cartopy.feature.BORDERS, linestyle=':', linewidth=0.5)

        # Scatter plot with colored dots for each basin type
        colors = ['blue', 'green', 'red', 'cyan', 'magenta', 'yellow']
        for basin_type in range(6):
            indices = np.where(ocean_basin == basin_type)[0]
            ax.scatter(lon[indices], lat[indices], color=colors[basin_type], label=f'Basin {basin_type}', alpha=0.7)

        # Add a legend
        plt.legend(loc='lower left')
        # Add title and show plot
        plt.title('Ocean Basins Plot using Cartopy')
        plt.savefig(png_file, dpi=300)
