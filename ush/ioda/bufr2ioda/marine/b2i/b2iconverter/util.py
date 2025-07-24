import os
import sys
import argparse
import subprocess
import numpy as np
import tempfile
import hashlib


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--config',
        type=str,
        help='Input JSON or YAML configuration', required=True
    )
    parser.add_argument(
        '-l', '--log_file',
        type=str,
        help='Output file for testing ioda variables'
    )
    parser.add_argument(
        '-t', '--test',
        type=str,
        help='Input test reference file'
    )
    args = parser.parse_args()
    config_file = args.config
    log_file = args.log_file
    test_file = args.test
    script_name = sys.argv[0]
    return script_name, config_file, log_file, test_file


def log_variable(logger, v_name, v):
    logger.debug(f"{v_name}: {len(v)}, {v.dtype}    min, max = {v.min()}, {v.max()}")


def run_diff(file1, file2, logger):
    try:
        # Run the diff command
        result = subprocess.run(
            ['diff', file1, file2],
            capture_output=True, text=True, check=False
        )

        # Check if diff command succeeded (return code 0)
        if result.returncode == 0:
            pass
        elif result.returncode == 1:
            logger.error("running diff on files:")
            logger.error(f">>> {file1}")
            logger.error(f">>> {file2}")
            logger.error("Files are different:")
            logger.error(f"{result.stdout}")
        else:
            logger.error("Error occurred while running diff command.")
            logger.error(f"{result.stdout}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")

    return result.returncode


# use hash for testing;
def compute_hash(sequence, algorithm='sha256'):
    """
    Compute a hash of the given sequence using the specified algorithm.

    :param sequence: A sequence of numbers (e.g., list of integers).
    :param algorithm: The hash algorithm to use (e.g., 'sha256').
    :return: The hexadecimal digest of the hash.
    """
    # Convert the sequence to a byte string
    sequence_bytes = bytes(sequence)
    # Create a hash object
    hash_obj = hashlib.new(algorithm)
    # Update the hash object with the byte string
    hash_obj.update(sequence_bytes)
    # Return the hexadecimal digest of the hash
    return hash_obj.hexdigest()


#####################################################################

def clean_lat_lon(lat, lon):
    """
    return a mask for valid pairs of latitude and longitude.

    Parameters:
    lat : array-like or None
        Latitude values, expected in [-90, 90].
    lon : array-like or None
        Longitude values, all in [-180, 180] or all in [0, 360].

    Returns:
    mask : numpy.ndarray
        Boolean mask (same shape as inputs), True for valid lat/lon pairs.
        Use to filter other arrays (e.g., other_data[mask]).
    """
    # Handle undefined or None inputs
    if lat is None or lon is None:
        return np.array([], dtype=bool)

    # Convert inputs to NumPy arrays, preserving masked arrays
    try:
        lat = np.asarray(lat, dtype=float)
        lon = np.asarray(lon, dtype=float)
    except (ValueError, TypeError):
        return np.zeros_like(lat, dtype=bool)

    # Ensure arrays have the same shape
    # probably needs to throw an exception
    if lat.shape != lon.shape:
        return np.zeros_like(lat, dtype=bool)

    # Initialize mask (True for valid, False for invalid)
    mask = np.ones(lat.shape, dtype=bool)

    # Handle masked arrays
    if np.ma.isMaskedArray(lat):
        mask &= ~lat.mask
    if np.ma.isMaskedArray(lon):
        mask &= ~lon.mask

    # Validate latitude: must be in [-90, 90]
    mask &= (lat >= -90) & (lat <= 90) & ~np.isnan(lat)

    # Validate longitude: all in [-180, 180] or all in [0, 360]
    valid_lons = lon[mask]  # Longitudes where lat is valid
    if len(valid_lons) == 0:
        return mask

    # Check longitude range consistency
    in_neg180_180 = (valid_lons >= -180) & (valid_lons <= 180)
    in_0_360 = (valid_lons >= 0) & (valid_lons <= 360)

    # Determine if all valid longitudes are in one range
    all_neg180_180 = np.all(in_neg180_180)
    all_0_360 = np.all(in_0_360)

    # If neither range is fully consistent, use dominant range
    # if the fraction of the "other" range is too large,
    # probably needs to throw an error
    if not (all_neg180_180 or all_0_360):
        if np.sum(in_neg180_180) >= np.sum(in_0_360):
            mask &= (lon >= -180) & (lon <= 180)
        else:
            mask &= (lon >= 0) & (lon <= 360)
    else:
        if all_neg180_180:
            mask &= (lon >= -180) & (lon <= 180)
        else:
            mask &= (lon >= 0) & (lon <= 360)

    # Ensure no NaN in longitude
    mask &= ~np.isnan(lon)

    return mask
#####################################################################


def write_date_time(obsspace, dateTime):
    obsspace.create_var(
        'MetaData/dateTime',
        dtype=dateTime.dtype, fillval=dateTime.fill_value
    ) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(dateTime)


def write_rcpt_date_time(obsspace, rcptdateTime):
    obsspace.create_var(
        'MetaData/rcptdateTime',
        dtype=rcptdateTime.dtype, fillval=rcptdateTime.fill_value
    ) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'receipt Datetime') \
        .write_data(rcptdateTime)


def write_longitude(obsspace, lon):
    obsspace.create_var(
        'MetaData/longitude',
        dtype=lon.dtype, fillval=lon.fill_value
    ) \
        .write_attr('units', 'degrees_east') \
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
        .write_attr('long_name', 'Longitude') \
        .write_data(lon)


def write_latitude(obsspace, lat):
    obsspace.create_var(
        'MetaData/latitude',
        dtype=lat.dtype, fillval=lat.fill_value
    ) \
        .write_attr('units', 'degrees_north') \
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
        .write_attr('long_name', 'Latitude') \
        .write_data(lat)


def write_station_id(obsspace, stationID):
    obsspace.create_var(
        'MetaData/stationID',
        dtype=stationID.dtype, fillval=stationID.fill_value
    ) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(stationID)


def write_depth(obsspace, depth):
    obsspace.create_var(
        'MetaData/depth',
        dtype=depth.dtype,
        fillval=depth.fill_value
    ) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Water depth') \
        .write_data(depth)


def write_seq_num(obsspace, seqNum, datatype, fillvalue):
    obsspace.create_var(
        'MetaData/sequenceNumber',
        dtype=datatype,
        fillval=fillvalue
    ) \
        .write_attr('long_name', 'Sequence Number') \
        .write_data(seqNum)


def write_obs_error(obsspace, v_name, units, v):
    obsspace.create_var(
        v_name,
        dtype=v.dtype, fillval=v.fill_value
    ) \
        .write_attr('units', units) \
        .write_attr('long_name', 'ObsError') \
        .write_data(v)


def write_ocean_basin(obsspace, ocean_basin, datatype, fillvalue):
    obsspace.create_var(
        'MetaData/oceanBasin',
        dtype=datatype,
        fillval=fillvalue
    ) \
        .write_attr('long_name', 'Ocean basin') \
        .write_data(ocean_basin)
