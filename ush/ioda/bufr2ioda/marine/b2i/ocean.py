#!/usr/bin/env python3

# import sys
import numpy as np
import numpy.ma as ma
# import os
# import argparse
import math
# import calendar
# import time
# import copy
# from datetime import datetime
# import json
# from pyiodaconv import bufr
# from collections import namedtuple
# from pyioda import ioda_obs_space as ioda_ospace
# from wxflow import Logger
# import warnings
# # suppress warnings
# warnings.filterwarnings('ignore')
# import subprocess
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import netCDF4 as nc
import xarray as xr



ocean_basin_nc_path = "/scratch2/NCEPDEV/ocean/Guillaume.Vernieres/data/static/common/RECCAP2_region_masks_all_v20221025.nc"

ocean_basin_filename = "ocean_basin180x360"
n1 = 180
n2 = 360

lat = [-89.5, -88.5, -87.5, -86.5, -85.5, -84.5, -83.5, -82.5, -81.5, -80.5, 
    -79.5, -78.5, -77.5, -76.5, -75.5, -74.5, -73.5, -72.5, -71.5, -70.5, 
    -69.5, -68.5, -67.5, -66.5, -65.5, -64.5, -63.5, -62.5, -61.5, -60.5, 
    -59.5, -58.5, -57.5, -56.5, -55.5, -54.5, -53.5, -52.5, -51.5, -50.5, 
    -49.5, -48.5, -47.5, -46.5, -45.5, -44.5, -43.5, -42.5, -41.5, -40.5, 
    -39.5, -38.5, -37.5, -36.5, -35.5, -34.5, -33.5, -32.5, -31.5, -30.5, 
    -29.5, -28.5, -27.5, -26.5, -25.5, -24.5, -23.5, -22.5, -21.5, -20.5, 
    -19.5, -18.5, -17.5, -16.5, -15.5, -14.5, -13.5, -12.5, -11.5, -10.5, 
    -9.5, -8.5, -7.5, -6.5, -5.5, -4.5, -3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 
    2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 
    15.5, 16.5, 17.5, 18.5, 19.5, 20.5, 21.5, 22.5, 23.5, 24.5, 25.5, 26.5, 
    27.5, 28.5, 29.5, 30.5, 31.5, 32.5, 33.5, 34.5, 35.5, 36.5, 37.5, 38.5, 
    39.5, 40.5, 41.5, 42.5, 43.5, 44.5, 45.5, 46.5, 47.5, 48.5, 49.5, 50.5, 
    51.5, 52.5, 53.5, 54.5, 55.5, 56.5, 57.5, 58.5, 59.5, 60.5, 61.5, 62.5, 
    63.5, 64.5, 65.5, 66.5, 67.5, 68.5, 69.5, 70.5, 71.5, 72.5, 73.5, 74.5, 
    75.5, 76.5, 77.5, 78.5, 79.5, 80.5, 81.5, 82.5, 83.5, 84.5, 85.5, 86.5, 
    87.5, 88.5, 89.5 ]

lon = [ 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 
    13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5, 21.5, 22.5, 23.5, 24.5, 
    25.5, 26.5, 27.5, 28.5, 29.5, 30.5, 31.5, 32.5, 33.5, 34.5, 35.5, 36.5, 
    37.5, 38.5, 39.5, 40.5, 41.5, 42.5, 43.5, 44.5, 45.5, 46.5, 47.5, 48.5, 
    49.5, 50.5, 51.5, 52.5, 53.5, 54.5, 55.5, 56.5, 57.5, 58.5, 59.5, 60.5, 
    61.5, 62.5, 63.5, 64.5, 65.5, 66.5, 67.5, 68.5, 69.5, 70.5, 71.5, 72.5, 
    73.5, 74.5, 75.5, 76.5, 77.5, 78.5, 79.5, 80.5, 81.5, 82.5, 83.5, 84.5, 
    85.5, 86.5, 87.5, 88.5, 89.5, 90.5, 91.5, 92.5, 93.5, 94.5, 95.5, 96.5, 
    97.5, 98.5, 99.5, 100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 
    108.5, 109.5, 110.5, 111.5, 112.5, 113.5, 114.5, 115.5, 116.5, 117.5, 
    118.5, 119.5, 120.5, 121.5, 122.5, 123.5, 124.5, 125.5, 126.5, 127.5, 
    128.5, 129.5, 130.5, 131.5, 132.5, 133.5, 134.5, 135.5, 136.5, 137.5, 
    138.5, 139.5, 140.5, 141.5, 142.5, 143.5, 144.5, 145.5, 146.5, 147.5, 
    148.5, 149.5, 150.5, 151.5, 152.5, 153.5, 154.5, 155.5, 156.5, 157.5, 
    158.5, 159.5, 160.5, 161.5, 162.5, 163.5, 164.5, 165.5, 166.5, 167.5, 
    168.5, 169.5, 170.5, 171.5, 172.5, 173.5, 174.5, 175.5, 176.5, 177.5, 
    178.5, 179.5, 180.5, 181.5, 182.5, 183.5, 184.5, 185.5, 186.5, 187.5, 
    188.5, 189.5, 190.5, 191.5, 192.5, 193.5, 194.5, 195.5, 196.5, 197.5, 
    198.5, 199.5, 200.5, 201.5, 202.5, 203.5, 204.5, 205.5, 206.5, 207.5, 
    208.5, 209.5, 210.5, 211.5, 212.5, 213.5, 214.5, 215.5, 216.5, 217.5, 
    218.5, 219.5, 220.5, 221.5, 222.5, 223.5, 224.5, 225.5, 226.5, 227.5, 
    228.5, 229.5, 230.5, 231.5, 232.5, 233.5, 234.5, 235.5, 236.5, 237.5, 
    238.5, 239.5, 240.5, 241.5, 242.5, 243.5, 244.5, 245.5, 246.5, 247.5, 
    248.5, 249.5, 250.5, 251.5, 252.5, 253.5, 254.5, 255.5, 256.5, 257.5, 
    258.5, 259.5, 260.5, 261.5, 262.5, 263.5, 264.5, 265.5, 266.5, 267.5, 
    268.5, 269.5, 270.5, 271.5, 272.5, 273.5, 274.5, 275.5, 276.5, 277.5, 
    278.5, 279.5, 280.5, 281.5, 282.5, 283.5, 284.5, 285.5, 286.5, 287.5, 
    288.5, 289.5, 290.5, 291.5, 292.5, 293.5, 294.5, 295.5, 296.5, 297.5, 
    298.5, 299.5, 300.5, 301.5, 302.5, 303.5, 304.5, 305.5, 306.5, 307.5, 
    308.5, 309.5, 310.5, 311.5, 312.5, 313.5, 314.5, 315.5, 316.5, 317.5, 
    318.5, 319.5, 320.5, 321.5, 322.5, 323.5, 324.5, 325.5, 326.5, 327.5, 
    328.5, 329.5, 330.5, 331.5, 332.5, 333.5, 334.5, 335.5, 336.5, 337.5, 
    338.5, 339.5, 340.5, 341.5, 342.5, 343.5, 344.5, 345.5, 346.5, 347.5, 
    348.5, 349.5, 350.5, 351.5, 352.5, 353.5, 354.5, 355.5, 356.5, 357.5, 
    358.5, 359.5 ]


class OceanBasin:
    # def __init__(self, filename):
    def __init__(self):
        self.__latitudes = lat
        self.__longitudes = lon
        self.__basin_array = None
        # if filename:
            # self.__basin_array = self.read_from_file(filename)



    def read_basin_from_file(self, filename):
        integers_list = []
        with open(filename, 'r') as file:
            for line in file:
                # Convert each line to an integer and append to the list
                integers_list.append(int(line.strip()))

        array_1d = np.array(integers_list)
        try:
            self.__basin_array = np.reshape(array_1d, (n1, n2))
        except ValueError:
            print(f"Cannot reshape the array of size {len(integers_list)} into ({n1}, {n2})")



    def print_basin(self):
        for i in range(n1):
            for j in range(n2):
                print(i, j, self.__basin_array[i][j])



    def read_nc_file(self, filename):
        print("reading the ocean basin data from ", filename)
        variable_name = 'open_ocean'

        with nc.Dataset(filename, 'r') as nc_file:
            if variable_name in nc_file.variables:
                variable = nc_file.variables[variable_name]

                lon_dim = nc_file.dimensions['lon'].size
                lat_dim = nc_file.dimensions['lat'].size
                print("ocean basin dimensions ", lon_dim, lat_dim)

                # Read the variable data into a numpy array
                variable_data = variable[:]

                # Convert to 2D numpy array (lon x lat)
                self.__basin_array = np.reshape(variable_data, (lat_dim, lon_dim))

                print(f'basin array array shape: {self.__basin_array.shape}')
                # print(f'Variable "{self.__basin_array}" shape: {self.__basin_array.shape}')
                # print(self.__basin_array)

        # print("DONE reading the ocean basin data from ", filename)




    def plot_basin(self):
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
    def get_station_basin(self, lat, lon):
        n = len(lon)

        lat0 = self.__latitudes[0]
        dlat = self.__latitudes[1] - self.__latitudes[0]
        lon0 = self.__longitudes[0]
        dlon = self.__longitudes[1] - self.__longitudes[0]
        # print("MMMMMMMMMMMMMuuuuuuuuuuuuuuuuuuuuuu")
        # print("MMMMMMMMMMMMM", lon0, lat0)
        # print("MMMMMMMMMMMMM", dlon, dlat)
        # print("MMMMMMMMMMMMMuuuuuuuuuuuuuuuuuuuuuu")

        # the data may be a masked array
        ocean_basin = []
        for i in range(n):
            if not ma.is_masked(lat[i]):
                i1 = round((lat[i] - lat0) / dlat)
                i2 = round((lon[i] - lon0) / dlon)
                ocean_basin.append(self.__basin_array[i1][i2])

            # if (i == 0):
                # print("MMMMMMMMMMMMM", lon[i], lat[i])
                # print("MMMMMMMMMMMMM", i1, i2)
                # print("MMMMMMMMMMMMM", self.__basin_array[i1][i2])

        return ocean_basin



    def print_station_basins(self, lon, lat):
        ocean_basin = self.get_station_basin(lat, lon)
        file_path = "/scratch1/NCEPDEV/da/Edward.Givelberg/workflow06112024/global-workflow/sorc/gdas.cd/ush/ioda/bufr2ioda/marine/argo.txt"
        # print("print_station_basins to ===============>")
        # print(file_path)
        with open(file_path, 'w') as file:
            # Iterate over lon, lat, and ocean_basin arrays simultaneously
            for lat_val, lon_val, basin_val in zip(lat, lon, ocean_basin):
                file.write(f"{lat_val} {lon_val} {basin_val}\n")




    def plot_stations(self, lon, lat):
        ocean_basin = self.get_station_basin(lon, lat)

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
        plt.savefig('/scratch1/NCEPDEV/da/Edward.Givelberg/workflow06112024/global-workflow/sorc/gdas.cd/ush/ioda/bufr2ioda/marine/argo.png', dpi=300)



    def copy2_nc4_file(self, input_file, output_file):

        filename = "/scratch1/NCEPDEV/stmp2/Edward.Givelberg/RUNDIRS/GFSv17-3DVAR-C384mx025/prepoceanobs.114138/gdas.t06z.insitu_profile_argo.2021063006.nc4"
        filename_w_ocean = filename + "_w_basin"
        filename_w_ocean = "/scratch1/NCEPDEV/da/Edward.Givelberg/workflow06112024/global-workflow/sorc/gdas.cd/ush/ioda/bufr2ioda/marine/jocean.nc4"
        print("add_basin_to_nc_file: .............")
        print("FILE = ", filename)
        input_file = filename
        output_file = filename_w_ocean

        # open your dataset
        ds = xr.open_dataset(filename)

        # change an existing variable
        # ds.your_var += 20

        # add a new variable
        # ds['new_var'] = xr.DataArray([1, 2, 3, 4], dims=('new_dim', ))

        # write to a new file
        ds.to_netcdf(filename_w_ocean)



    def copy_nc4_file(self, input_file, output_file):

        filename = "/scratch1/NCEPDEV/stmp2/Edward.Givelberg/RUNDIRS/GFSv17-3DVAR-C384mx025/prepoceanobs.114138/gdas.t06z.insitu_profile_argo.2021063006.nc4"
        filename_w_ocean = filename + "_w_basin"
        filename_w_ocean = "/scratch1/NCEPDEV/da/Edward.Givelberg/workflow06112024/global-workflow/sorc/gdas.cd/ush/ioda/bufr2ioda/marine/jocean.nc4"
        print("add_basin_to_nc_file: .............")
        print("FILE = ", filename)
        input_file = filename
        output_file = filename_w_ocean

        # Open the input NetCDF4 file for reading
        with nc.Dataset(input_file, 'r') as ds:
            # Create a new NetCDF4 file for writing
            with nc.Dataset(output_file, 'w') as ds_out:
                # Loop through and copy global attributes
                for attr_name in ds.ncattrs():
                    ds_out.setncattr(attr_name, ds.getncattr(attr_name))
                
                # Loop through and copy dimensions
                for dim_name, dim in ds.dimensions.items():
                    ds_out.createDimension(dim_name, len(dim) if not dim.isunlimited() else None)
                
                # Loop through and copy groups recursively
                def copy_group(src_group, dst_group):
                    for attr_name in src_group.ncattrs():
                        dst_group.setncattr(attr_name, src_group.getncattr(attr_name))
                    
                    for dim_name, dim in src_group.dimensions.items():
                        dst_group.createDimension(dim_name, len(dim) if not dim.isunlimited() else None)
                    
                    for var_name, var in src_group.variables.items():
                        new_var = dst_group.createVariable(var_name, var.dtype, var.dimensions)
                        
                        for attr_name in var.ncattrs():
                            setattr(new_var, attr_name, getattr(var, attr_name))
                        
                        new_var[:] = var[:]
                    
                    for subgrp_name, subgrp in src_group.groups.items():
                        new_subgrp = dst_group.createGroup(subgrp_name)
                        copy_group(subgrp, new_subgrp)
                
                # Start copying from the root group
                copy_group(ds, ds_out)




    def add_basin_to_nc_file(self, filename):

        filename = "/scratch1/NCEPDEV/stmp2/Edward.Givelberg/RUNDIRS/GFSv17-3DVAR-C384mx025/prepoceanobs.114138/gdas.t06z.insitu_profile_argo.2021063006.nc4"
        filename_w_ocean = filename + "_w_basin"
        filename_w_ocean = "/scratch1/NCEPDEV/da/Edward.Givelberg/workflow06112024/global-workflow/sorc/gdas.cd/ush/ioda/bufr2ioda/marine/jocean.nc4"
        print("add_basin_to_nc_file: .............")
        print("FILE = ", filename)

        # Open the existing NetCDF file for reading
        with nc.Dataset(filename, 'r') as ds:
            # Open a new NetCDF file for writing
            with nc.Dataset(filename_w_ocean, 'w') as ds_out:
                # Iterate over dimensions and create them in the new file
                for dimname, dim in ds.dimensions.items():
                    ds_out.createDimension(dimname, len(dim) if not dim.isunlimited() else None)
        
                # Iterate over variables and copy them to the new file
                for varname, var in ds.variables.items():
                    # Create the variable in the new file
                    new_var = ds_out.createVariable(varname, var.dtype, var.dimensions)
            
                    # Copy variable attributes
                    new_var.setncatts({k: var.getncattr(k) for k in var.ncattrs()})
            
                    # Copy variable data
                    new_var[:] = var[:]
        
                # Add your new variable (example: calculated based on an existing variable)
                # temperature = ds.variables['temperature'][:]  # Example existing variable
                # new_variable = temperature * 2  # Example calculation
        
                # Create a new variable in the new file
                # new_var_name = 'new_variable'
                # new_var_units = 'units'  # Example units
                # new_var_long_name = 'Long name of new variable'  # Example long_name
                # new_var = ds_out.createVariable(new_var_name, temperature.dtype, temperature.dimensions)
        
                # Set variable attributes
                # new_var.units = new_var_units
                # new_var.long_name = new_var_long_name
             
                # Assign data to the new variable
                # new_var[:] = new_variable
        
                # Copy global attributes
                ds_out.setncatts({k: ds.getncattr(k) for k in ds.ncattrs()})




if __name__ == '__main__':

    ocean_basin = OceanBasin()

    # ocean_basin.read_basin_from_file(ocean_basin_filename)

    ocean_basin.read_nc_file(ocean_basin_nc_path)

    # ocean_basin.print_basin()
    ocean_basin.plot_basin()

