import netCDF4 as nc
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import cartopy.crs as ccrs

def get_sst(file_path = "ghrsst_sst_mb_20210701.ioda.bin10.nc", group='ObsValue', var='seaSurfaceTemperature'):
    dataset = nc.Dataset(file_path)

    #metadata_group = dataset.groups['MetaData']
    #lon = metadata_group.variables['longitude'][:]
    #lat = metadata_group.variables['latitude'][:]

    # Access the ObsValue group
    obs_value_group = dataset.groups[group]

    # Access the seaSurfaceTemperature variable
    sst_variable = obs_value_group.variables[var]

    # Read the seaSurfaceTemperature data
    sst_data = sst_variable[:]

    # Close the NetCDF file
    dataset.close()
    return sst_data

seconds_since_reference = 1277935232
reference_date = datetime(1981, 1, 1, 0, 0, 0)
result_date = reference_date + timedelta(seconds=seconds_since_reference)
formatted_date = result_date.strftime('%Y-%m-%d %H:%M:%S')
print("The date and time is:", formatted_date)

# Ref time diff between old and new
date1 = datetime(1970, 1, 1, 0, 0, 0)
date2 = datetime(1981, 1, 1, 0, 0, 0)
time_difference = (date2 - date1).total_seconds()


plt.figure(figsize=(18, 10))
cnt = 1
var='seaSurfaceTemperature'
for group in ['ObsValue', 'ObsError', 'PreQC']:
    plt.subplot(3,3,cnt)
    # New converter
    new = get_sst(file_path = "test.ioda.new.nc", group=group, var=var)
    str_label=f'New: min={np.min(new)}, max={np.max(new)}, nobs={len(new)}'
    plt.hist(new, bins=150, color='b', alpha=0.2, label=str_label)

    # Old converter
    old = get_sst(file_path='sst.ioda.old.nc', group=group, var=var)
    str_label=f'Old: min={np.min(old)}, max={np.max(old)}, nobs={len(old)}'
    plt.hist(old, bins=150, color='r', alpha=0.2, label=str_label)
    plt.title(group)
    plt.grid(True)
    plt.legend(prop={'size': 6})
    cnt += 1

group = 'MetaData'
for var in ['dateTime', 'longitude', 'latitude']:
    plt.subplot(3,3,cnt)
    # New converter
    new = get_sst(file_path = "test.ioda.new.nc", group=group, var=var)
    str_label=f'New: min={np.min(new)}, max={np.max(new)}, nobs={len(new)}'
    plt.hist(new, bins=150, color='b', alpha=0.2, label=str_label)

    # Old converter
    old = get_sst(file_path='sst.ioda.old.nc', group=group, var=var)
    if (var == 'dateTime'):
        old = old - time_difference

    str_label=f'Old: min={np.min(old)}, max={np.max(old)}, nobs={len(old)}'
    plt.hist(old, bins=150, color='r', alpha=0.2, label=str_label)
    plt.title(var)
    plt.grid(True)
    plt.legend(prop={'size': 6})
    cnt += 1

# Scatter plots
lon = get_sst(file_path = "test.ioda.new.nc", group="MetaData", var="longitude")
lat = get_sst(file_path = "test.ioda.new.nc", group="MetaData", var="latitude")
sst = get_sst(file_path = "test.ioda.new.nc", group="ObsValue", var="seaSurfaceTemperature")
time = get_sst(file_path = "test.ioda.new.nc", group="MetaData", var="dateTime")
plt.subplot(3,3,7)
sc0 = plt.scatter(lon, lat, c=sst, cmap='viridis', s=1, marker='.')
plt.colorbar(sc0, orientation='horizontal', shrink=0.5)
plt.title('sst')

plt.subplot(3,3,8)
sc1 = plt.scatter(lon, lat, c=time, cmap='viridis', s=1, marker='.')
plt.colorbar(sc1, orientation='horizontal', shrink=0.5)
plt.title('dateTime')

plt.suptitle('GHRSST', fontweight='bold')
#plt.tight_layout()
plt.savefig('GHRSST (superobed)')
plt.show()
