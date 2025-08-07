# Flood Class for Tripolar-to-Gaussian Testing

## Overview

The `Flood` class provides tripolar to Gaussian grid interpolation functionality for testing purposes. It follows the standard OOPS Application pattern and integrates with the GDAS application framework.

## Usage

The Flood application can be run using the `gdas.x` executable:

```bash
./gdas.x <traits> flood <config.yaml>
```

Where:
- `<traits>`: Either "fv3jedi" or "soca"
- `flood`: The application name
- `<config.yaml>`: Configuration file (see example below)

## Example Configuration

```yaml
input geometry:
  type: tripolar
  nx: 360
  ny: 180

output geometry:
  type: gaussian
  nlat: 192
  nlon: 384

input state:
  filename: input_tripolar_state.nc
  date: 2023-12-01T00:00:00Z

output file: output_gaussian_state.nc

variables:
  - temperature
  - humidity
  - pressure

interpolation method: tripolar_to_gaussian
```

## Parameters

- **input geometry**: Configuration for the input tripolar grid
- **output geometry**: Configuration for the output Gaussian grid  
- **input state**: Input state file and metadata
- **output file**: Output file path
- **variables**: List of variables to interpolate
- **interpolation method**: Interpolation algorithm (default: "tripolar_to_gaussian")

## Implementation Notes

This implementation uses the OOPS `changeResolution` method for the actual interpolation. In a production environment, this could be replaced with more sophisticated tripolar-to-Gaussian interpolation algorithms.

## Files

- `mains/Flood.h`: Header file with class definition and parameters
- `mains/Flood.cc`: Implementation file
- `test/example_flood_config.yaml`: Example configuration file