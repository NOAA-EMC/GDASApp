# a simple script to plot stations
# Usage:  python3 bufr_plot_stations.py -i BUFR_FILE_NAME
# output is produced in the file "stations.png"

# the bufr query strings will not always work;
# in some cases they need to be changed to CLONH, CLATH

import argparse

from pyiodaconv import bufr

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
# from .ocean import OceanBasin


def plot_points_on_map(latitudes, longitudes, output_file_name, title='Map with Points', marker_color='red', marker_size=50):
    """
    Plots points on a map given lists of latitudes and longitudes.

    Parameters:
    latitudes (list of float): List of latitude values for the points.
    longitudes (list of float): List of longitude values for the points.
    title (str): Title of the map (default is 'Map with Points').
    marker_color (str): Color of the markers (default is 'red').
    marker_size (int): Size of the markers (default is 50).
    """
    # Create a new figure
    fig, ax = plt.subplots(figsize=(10, 7), subplot_kw={'projection': ccrs.PlateCarree()})

    # Add features to the map
    ax.add_feature(cfeature.LAND, edgecolor='black')
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.add_feature(cfeature.LAKES, edgecolor='black')

    # Add gridlines
    ax.gridlines(draw_labels=True)

    # Plot each point
    ax.scatter(longitudes, latitudes, color=marker_color, s=marker_size, edgecolor='black', transform=ccrs.PlateCarree())

    # Set title
    plt.title(title)

    # Show the map
    # plt.show()
    plt.savefig(output_file_name, dpi=300)


parser = argparse.ArgumentParser()
parser.add_argument(
    '-i', '--input',
    type=str,
    help='Input BUFR filename', required=True
)
parser.add_argument(
    '-o', '--output',
    type=str,
    help='Output png filename', required=True
)
args = parser.parse_args()
bufrfile_path = args.input
output_file_name = args.output

q = bufr.QuerySet()
q.add('longitude', '*/CLON')
q.add('latitude', '*/CLAT')

with bufr.File(bufrfile_path) as f:
    r = f.execute(q)

print("Executed query")

lon = r.get('longitude')
lat = r.get('latitude')

print(f"read lat, lon -- {len(lon)} points")

plot_points_on_map(lat, lon, output_file_name, title='stations', marker_color='blue', marker_size=10)
