# GDAS Ocean and Sea Ice Relaxation Implementation

## Overview

The relaxation functionality in GDAS provides a mechanism to nudge ocean and sea ice analysis increments toward climatological or observationally-constrained relaxation fields. This implementation allows for temporally-interpolated relaxation with configurable regional filtering and physically-based quality control.

## Key Features

- **Temporal Interpolation**: Monthly relaxation fields are interpolated to the analysis time
- **Regional Control**: Selective relaxation by ocean basin (Arctic, Antarctic, etc.)
- **Variable-Specific Configuration**: Different relaxation time scales for ocean vs. ice variables
- **Quality Control**: Physics-based bounds checking using field metadata
- **Flood Filling**: Gap-filling for masked regions using spatial extrapolation

## Implementation Architecture

### Core Components

1. **`gdas_relaxation_incr.cc/h`**: Main relaxation increment computation
2. **`gdas_incr_qc.h`**: Integration with increment quality control and regional filtering
3. **`fields_metadata.yaml`**: Physical bounds and fill values for variables

### Workflow

```
Background State + DA Increment
         ↓
Load Monthly Relaxation Fields (prev/next month)
         ↓
Temporal Interpolation to Analysis Time
         ↓
Quality Control & Gap Filling
         ↓
Compute Relaxation Increment: relax - (background + increment)
         ↓
Apply Regional Filtering (Arctic/Antarctic control)
         ↓
Weighted Combination: final = w_da * increment + w_relax * relax_increment
```

## Configuration

### Basic Relaxation Setup

```yaml
relaxation:
  # Path to relaxation field files
  basename: "./relaxation"

  # Ocean relaxation file template (%mm replaced with month)
  ocn_filename: "ocean.relax_%mm.nc"

  # Optional: Ice relaxation file template
  ice_filename: "ice.relax_%mm.nc"

  # Field metadata for bounds checking
  fields metadata: "parm/marine/fields_metadata.yaml"

  # DA window and relaxation time scales
  da window: 6.0  # hours

  ocean:
    relaxation time: 168.0  # hours (7 days)

  ice:
    relaxation time: 240.0  # hours (10 days)

    # Variables to relax in each region
    arctic variables:
      - "sea_ice_thickness"
      - "sea_ice_snow_thickness"

    antarctic variables:
      - "sea_ice_thickness"
      # Note: snow thickness omitted for Antarctic
```

### Field Metadata Configuration

In `fields_metadata.yaml`:

```yaml
- name: sea_water_potential_temperature
  min valid: -5.0
  max valid: 50.0
  fill value: 0.0

- name: sea_water_salinity
  min valid: 0.0
  max valid: 50.0
  fill value: 35.0

- name: sea_ice_thickness
  min valid: 0.0
  max valid: 10.0
  fill value: 0.0

- name: sea_ice_snow_thickness
  min valid: 0.0
  max valid: 5.0
  fill value: 0.0
```

## Formulation

### Temporal Interpolation

Monthly relaxation fields are anchored to the 15th of each month and linearly interpolated to the analysis time using the two nearest monthly fields.

### Relaxation Increment

```
relax_increment = interpolated_relaxation_field - (background + da_increment)
```

### Relaxation Time Scale

The relaxation time (`tau`) controls how strongly the relaxation field influences the final analysis. It represents the e-folding time scale over which the system would relax to the climatological state:

```
w_da = 1 / (1 + dt_DA / tau)
```

- **Short relaxation time** (`tau` small): Strong relaxation toward climatology (`w_da` → 0)
- **Long relaxation time** (`tau` large): Weak relaxation, analysis increment dominates (`w_da` → 1)
- **Equal time scales** (`tau = dt_DA`): Balanced influence (`w_da = 0.5`)

### Final Weighted Combination

```
w_relax = 1 - w_da
final_increment = w_da * da_increment + w_relax * relax_increment
```

Where:
- `dt_DA`: DA window (hours)
- `tau`: relaxation time scale (hours, variable-dependent)

## Regional Filtering

### Sea Ice Regional Control

The implementation supports selective relaxation of sea ice variables by region:

```cpp
// Arctic region: latitude > 50°N
if (lat > 50.0) {
  bool relax_this_var = (variable in arctic_variables_list);
}

// Antarctic region: latitude < -60°S
if (lat < -50.0) {
  bool relax_this_var = (variable in antarctic_variables_list);
}
```

## Quality Control

### Physics-Based Bounds Checking

Instead of relying solely on NaN detection, the implementation uses physically meaningful bounds:

```cpp
bool isValid = std::isfinite(value) &&
               value >= min_valid &&
               value <= max_valid;
```

### Flood Filling

For regions where relaxation fields are masked or invalid:

1. **Create Binary Mask**: 1 for valid values, 0 for invalid
2. **Apply Flood Algorithm**: Extrapolate from valid neighboring points
3. **Iterate**: Continue until convergence or maximum iterations reached

## File Structure

### Relaxation Field Files

Expected directory structure:
```
relaxation/
├── ocean.relax_01.nc  # January ocean fields
├── ocean.relax_02.nc  # February ocean fields
├── ...
├── ocean.relax_12.nc  # December ocean fields
├── ice.relax_01.nc    # January ice fields (optional)
└── ...
```

### Required Variables

**Ocean Files:**
- `sea_water_potential_temperature`
- `sea_water_salinity`

**Ice Files (optional):**
- `sea_ice_thickness`
- `sea_ice_snow_thickness`
- Additional sea ice variables as needed

## Integration Points

### Increment Quality Control

The relaxation is integrated into the main increment QC workflow in `gdas_incr_qc.h`:

```cpp
if (config.has("relaxation")) {
  // Compute relaxation increment
  soca::Increment relaxIncr = computeRelaxationIncrement(xb, dx, geom, relaxConfig);

  // Apply weighted combination with regional filtering
  // ...
}
```

### Testing

Reproducibility tests ensure consistent results across different MPI configurations:

```cmake
# Test with 2 processes
test_gdasapp_utils_incrhandler_relaxation

# Test with 8 processes
test_gdasapp_utils_incrhandler_relaxation_8pes

# Verify reproducibility
test_gdasapp_utils_incrhandler_relaxation_reproducibility
```

## Error Handling

### Invalid Values

- **NaN/Infinite**: Replaced with variable-specific fill values
- **Out of Bounds**: Values outside physical ranges are masked
- **Missing Files**: Graceful degradation with warning messages

### Diagnostic Output

- **Debug Logging**: Detailed information about bounds, weights, and processing
- **Warning Messages**: Alert for invalid values and missing data
- **Summary Statistics**: Overview of processing results

## Performance Considerations

### Memory Usage

- Relaxation fields are loaded month-by-month to minimize memory footprint
- Temporal interpolation is performed in-place where possible

### Computational Efficiency

- Bounds checking is performed once per variable using metadata
- Flood filling uses optimized spatial algorithms
- Regional filtering uses simple latitude-based logic

## Future Enhancements

### Potential Extensions

1. **Dynamic Relaxation Scales**: Time-varying relaxation based on observation density
2. **Basin-Specific Control**: Extend regional filtering to ocean basins
3. **Multi-Scale Relaxation**: Different time scales for different spatial scales
4. **Adaptive Bounds**: Dynamically adjust bounds based on local conditions

### Configuration Improvements

1. **Validation**: Automatic validation of relaxation field consistency
2. **Diagnostics**: Enhanced output for monitoring relaxation effectiveness
3. **Flexibility**: Support for different temporal interpolation schemes

## Usage Examples

### Basic Ocean-Only Relaxation

```yaml
relaxation:
  basename: "/path/to/relaxation/fields"
  ocn_filename: "ocean_clim_%mm.nc"
  da window: 6.0
  ocean:
    relaxation time: 168.0
```

### Ocean + Sea Ice with Regional Control

```yaml
relaxation:
  basename: "/path/to/relaxation/fields"
  ocn_filename: "ocean_clim_%mm.nc"
  ice_filename: "ice_clim_%mm.nc"
  da window: 6.0
  ocean:
    relaxation time: 168.0
  ice:
    relaxation time: 240.0
    arctic variables: ["sea_ice_thickness"]
    antarctic variables: ["sea_ice_thickness", "sea_ice_snow_thickness"]
```

## References

- JEDI-SOCA Documentation: [SOCA Documentation](https://github.com/JCSDA-internal/soca)
- GDAS Workflow: [Global Workflow](https://github.com/NOAA-EMC/global-workflow)
- Atlas Library: [Atlas Documentation](https://github.com/ecmwf/atlas)
