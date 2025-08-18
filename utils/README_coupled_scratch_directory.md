# Coupled Scratch Directory Utility

This utility generates a coupled scratch directory containing all resources required to run both `soca` and `fv3-jedi` components for coupled ocean-atmosphere experiments.

## Features

- Creates a structured scratch directory with separate `fv3-jedi/` and `soca/` subdirectories
- Supports flexible input paths for static files and background data
- Can use project test data for development and testing
- Generates necessary configuration files (MOM6 input, MOM input)
- Self-contained output ready for coupled experiments

## Usage

### Basic Usage with Custom Files

```bash
./utils/generate_coupled_scratch_directory.py \
  --output-dir /path/to/scratch \
  --atm-static-dir /path/to/atmosphere/static \
  --ocean-static-dir /path/to/ocean/static \
  --atm-backgrounds /path/to/atm/bg1.nc /path/to/atm/bg2.nc \
  --ocean-backgrounds /path/to/ocean/bg.nc \
  --ice-backgrounds /path/to/ice/bg.nc
```

### Using Project Test Data

For development and testing, you can use the project's test data:

```bash
./utils/generate_coupled_scratch_directory.py \
  --output-dir /path/to/scratch \
  --use-test-data /path/to/GDASApp/utils
```

### Options

- `--output-dir`: Required. Directory where the coupled scratch directory will be created
- `--atm-static-dir`: Path to directory containing atmosphere static files
- `--ocean-static-dir`: Path to directory containing ocean static files
- `--atm-backgrounds`: List of atmosphere background files
- `--ocean-backgrounds`: List of ocean background files
- `--ice-backgrounds`: List of sea ice background files
- `--use-test-data`: Path to project source directory to use test data
- `--verbose, -v`: Enable verbose output

## Output Structure

The utility creates the following directory structure:

```
scratch_directory/
├── fv3-jedi/
│   ├── atmosphere_static_files...
│   ├── atmosphere_backgrounds...
│   ├── fmsmpp.nml (if available)
│   ├── field_table_ufs (if available)
│   └── oro_data.tile*.nc, sfc_data.tile*.nc (if test data used)
└── soca/
    ├── ocean_static_files...
    ├── ocean_backgrounds...
    ├── ice_backgrounds...
    ├── mom6_input.nml
    ├── MOM_input
    ├── fields_metadata.yaml (if available)
    ├── soca_gridspec.nc (if test data used)
    ├── INPUT/
    │   ├── grid_spec.nc (if test data used)
    │   └── ocean_mosaic.nc (if test data used)
    └── ocn.nc, ice.nc (if test data used)
```

## Requirements

- Python 3.6+
- Optional: `ncgen` tool (for generating NetCDF files from test data)
- Optional: `netCDF4` Python package (for advanced test data processing)

## Testing

Run the included test suite:

```bash
python3 utils/test_generate_coupled_scratch_directory.py
```

## Integration with Existing Scripts

This utility leverages and extends the functionality from:
- `utils/soca/test/generate_coupled_resources.py`
- `utils/soca/test/generate_soca_resources.py`

It provides a more flexible command-line interface while maintaining compatibility with the existing resource generation logic.