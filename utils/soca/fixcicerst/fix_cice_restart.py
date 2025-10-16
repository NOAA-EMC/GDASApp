#!/usr/bin/env python3
"""
Application to check and fix CICE6 restart files.

This script reads a YAML configuration file containing paths to CICE6 restart
files and upper bounds for ice and snow thickness. It creates new restart files
with sea ice state "zeroed out" where thicknesses exceed the defined maximums.
"""

import sys
import yaml
import numpy as np
from netCDF4 import Dataset
from pathlib import Path
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def load_config(config_file):
    """
    Load YAML configuration file.

    Expected format:
    cice_restart_path: "/path/to/restart.nc"
    max_ice_thickness: 10.0   # meters
    max_snow_thickness: 2.0   # meters
    output_path: "/path/to/fixed_restart.nc"  # optional
    """
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config file {config_file}: {e}")
        sys.exit(1)


def calculate_aggregated_thickness(vicen, vsnon):
    """
    Calculate aggregated ice and snow thickness across categories.

    Parameters:
    vicen: ice volume per unit area (ncat, nj, ni)
    vsnon: snow volume per unit area (ncat, nj, ni)

    Returns:
    ice_thickness: aggregated ice thickness (nj, ni)
    snow_thickness: aggregated snow thickness (nj, ni)
    """
    # Sum across categories (axis=0)
    ice_thickness = np.sum(vicen, axis=0)
    snow_thickness = np.sum(vsnon, axis=0)

    return ice_thickness, snow_thickness


def create_mask(ice_thickness, snow_thickness, max_ice, max_snow):
    """
    Create mask for points where ice or snow thickness exceeds limits.

    Returns:
    mask: True where thickness exceeds limits (should be zeroed)
    """
    ice_exceed = ice_thickness > max_ice
    snow_exceed = snow_thickness > max_snow

    # Mask is True where either ice or snow exceeds limits
    mask = ice_exceed | snow_exceed

    return mask


def zero_seaice_state(dataset, mask):
    """
    Zero out sea ice state variables where mask is True.

    Sea ice state variables to zero:
    - aicen: ice concentration
    - vicen: ice volume per unit area
    - vsnon: snow volume per unit area
    - Tsfcn: surface temperature
    - iage: ice age
    - alvl: level ice area fraction
    - vlvl: level ice volume per unit area
    - apnd: melt pond area fraction
    - hpnd: melt pond depth
    - ipnd: melt pond ice thickness
    - dhs: snow depth difference
    - ffrac: floe size distribution
    - sice*: sea ice salinity
    - qice*: ice enthalpy
    - qsno*: snow enthalpy
    """

    seaice_vars = [
        'aicen', 'vicen', 'vsnon', 'Tsfcn', 'iage', 'alvl', 'vlvl',
        'apnd', 'hpnd', 'ipnd', 'dhs', 'ffrac'
    ]

    # Add salinity and enthalpy variables
    for i in range(1, 8):  # sice001-007, qice001-007
        seaice_vars.extend([f'sice{i:03d}', f'qice{i:03d}'])

    # Add snow enthalpy (qsno001)
    seaice_vars.append('qsno001')

    points_modified = np.sum(mask)

    for var_name in seaice_vars:
        if var_name in dataset.variables:
            var = dataset.variables[var_name]

            if len(var.dimensions) == 3 and var.dimensions[0] == 'ncat':
                # Category-based variable (ncat, nj, ni)
                # Read all data, modify, then write back
                data = var[:]
                for cat in range(data.shape[0]):
                    data[cat, mask] = 0.0
                var[:] = data

                if points_modified > 0:
                    logger.info(f"Zeroed {points_modified} points for "
                                f"variable {var_name}")

            elif len(var.dimensions) == 2:
                # 2D variable (nj, ni)
                # Read data, modify, then write back
                data = var[:]
                data[mask] = 0.0
                var[:] = data

                if points_modified > 0:
                    logger.info(f"Zeroed {points_modified} points for "
                                f"variable {var_name}")

    return points_modified


def fix_cice_restart(config):
    """
    Main function to fix CICE restart file.
    """
    input_file = config['cice_restart_path']
    max_ice = config.get('max_ice_thickness', 10.0)
    max_snow = config.get('max_snow_thickness', 2.0)

    # Determine output file
    if 'output_path' in config:
        output_file = config['output_path']
    else:
        input_path = Path(input_file)
        output_file = input_path.parent / f"fixed_{input_path.name}"

    logger.info(f"Processing CICE restart: {input_file}")
    logger.info(f"Max ice thickness: {max_ice} m")
    logger.info(f"Max snow thickness: {max_snow} m")
    logger.info(f"Output file: {output_file}")

    try:
        # Open input file
        with Dataset(input_file, 'r') as src:
            ni_size = src.dimensions['ni'].size
            nj_size = src.dimensions['nj'].size
            ncat_size = src.dimensions['ncat'].size
            logger.info(f"Input file dimensions: ni={ni_size}, "
                        f"nj={nj_size}, ncat={ncat_size}")

            # Read ice and snow volumes
            vicen = src.variables['vicen'][:]
            vsnon = src.variables['vsnon'][:]

            # Calculate aggregated thicknesses
            ice_thickness, snow_thickness = calculate_aggregated_thickness(
                vicen, vsnon)

            # Create mask
            mask = create_mask(ice_thickness, snow_thickness,
                               max_ice, max_snow)

            ice_exceed = np.sum(ice_thickness > max_ice)
            snow_exceed = np.sum(snow_thickness > max_snow)
            logger.info(f"Points exceeding ice thickness limit: {ice_exceed}")
            logger.info(f"Points exceeding snow thickness limit: "
                        f"{snow_exceed}")
            logger.info(f"Total points to be zeroed: {np.sum(mask)}")

            if np.sum(mask) == 0:
                logger.info("No points exceed the thickness limits. "
                            "No changes needed.")
                return

            # Create output file (copy of input)
            with Dataset(output_file, 'w') as dst:
                # Copy dimensions
                for name, dim in src.dimensions.items():
                    size = len(dim) if not dim.isunlimited() else None
                    dst.createDimension(name, size)

                # Copy variables and attributes
                for name, var in src.variables.items():
                    dst_var = dst.createVariable(name, var.datatype,
                                                 var.dimensions)

                    # Copy attributes
                    attrs = {k: var.getncattr(k) for k in var.ncattrs()}
                    dst_var.setncatts(attrs)

                    # Copy data
                    dst_var[:] = var[:]

                # Copy global attributes
                dst.setncatts({k: src.getncattr(k) for k in src.ncattrs()})

                # Zero out sea ice state where needed
                points_modified = zero_seaice_state(dst, mask)

        logger.info(f"Fixed restart file written to: {output_file}")
        logger.info(f"Total grid points modified: {points_modified}")

    except Exception as e:
        logger.error(f"Error processing restart file: {e}")
        sys.exit(1)


def main():
    description = ("Fix CICE6 restart files by zeroing sea ice state "
                   "where thickness exceeds limits")
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "config_file",
        help="YAML configuration file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check thicknesses but don't create output file"
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config_file)

    # Validate required keys
    required_keys = ['cice_restart_path']
    for key in required_keys:
        if key not in config:
            logger.error(f"Required key '{key}' not found in config file")
            sys.exit(1)

    if args.dry_run:
        logger.info("DRY RUN MODE - no output file will be created")
        # TODO: Implement dry run logic
        return

    # Fix the restart file
    fix_cice_restart(config)


if __name__ == "__main__":
    main()
