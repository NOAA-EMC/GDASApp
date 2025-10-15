# CICE Restart File Fixing Utility

This utility checks CICE6 restart files for unrealistic ice and snow thickness values and creates corrected restart files with the sea ice state "zeroed out" at problematic grid points.

## Purpose

The tool addresses issues where CICE6 restart files contain unrealistically thick ice or snow that may cause model instability or unphysical behavior. When ice or snow thickness exceeds specified maximum values, all sea ice state variables at those grid points are set to zero, effectively creating open water conditions.

## Usage

```bash
python fix_cice_restart.py config.yaml
```

### Options

- `config.yaml`: YAML configuration file specifying input parameters

## Configuration File Format

The YAML configuration file must contain:

```yaml
# Required: Path to input CICE restart file
cice_restart_path: "/path/to/cice.r.yyyy-mm-dd-sssss.nc"

# Required: Maximum ice thickness threshold (meters)
max_ice_thickness: 10.0

# Required: Maximum snow thickness threshold (meters)
max_snow_thickness: 2.0

# Optional: Output file path
output_path: "/path/to/fixed_restart.nc"
```

If `output_path` is not specified, the output file will be named `fixed_<original_filename>` in the same directory as the input file.

## Sea Ice Variables Modified

When thickness limits are exceeded, the following CICE state variables are zeroed:

### Ice and Snow
- `aicen`: Ice concentration per category
- `vicen`: Ice volume per unit area per category
- `vsnon`: Snow volume per unit area per category

### Ice Physics
- `Tsfcn`: Surface temperature per category
- `iage`: Ice age
- `alvl`: Ridged Ice Area per Category
- `vlvl`: Ridged Ice Volume per Category

### Melt Ponds
- `apnd`: Melt pond area fraction
- `hpnd`: Melt pond depth
- `ipnd`: Melt pond ice thickness

### Thermodynamics
- `sice001`-`sice007`:Ice salinity per layer
- `qice001`-`qice007`: Ice enthalpy per layer
- `qsno001`: Snow enthalpy

### Other Variables
- `dhs`: change in mean snow thickness
- `ffrac`: mean fraction of fsurfn used to melt ipond

## Algorithm

1. **Read Configuration**: Parse YAML file for input parameters
2. **Load Restart File**: Open NetCDF restart file and read dimensions
3. **Calculate Thickness**: Sum ice/snow volumes across categories to get total thickness
4. **Create Mask**: Identify grid points where thickness exceeds limits
5. **Zero State Variables**: Set all sea ice variables to zero at masked points
6. **Write Output**: Create new restart file with corrections applied

## Dependencies

- Python 3.6+
- netCDF4
- numpy
- PyYAML

## Example

```bash
# Create configuration file
cat > config.yaml << EOF
cice_restart_path: "cice.r.2023-01-15-00000.nc"
max_ice_thickness: 8.0
max_snow_thickness: 1.5
output_path: "cice.r.2023-01-15-00000.fixed.nc"
EOF

# Run the fix
python fix_cice_restart.py config.yaml
```

## Output

The utility provides logging information about:
- Input file dimensions and statistics
- Number of grid points exceeding thickness limits
- Variables modified and number of points affected
- Output file location

## Notes

- The tool preserves all file attributes and metadata from the original restart file
- Only sea ice state variables are modified; ocean and atmospheric forcing remain unchanged
- Grid points with excessive thickness become open water (all sea ice variables = 0)
- The original restart file is not modified; a new corrected file is created
