# GDAS Increment Quality Control (Standalone Library)

A standalone C++ header-only library extracted from GDASApp for performing quality control on ocean data assimilation increments.

## Overview

This library provides quality control (QC) functionality to ensure that analysis increments in ocean data assimilation remain within physically meaningful bounds. The QC process ensures:

- The final analysis state stays within user-defined physical bounds
- The increment does not introduce new static instabilities in the water column
- The steric height increment remains within specified limits

## Features

### 1. Water Column Stability Check
Ensures that temperature and salinity increments do not introduce unrealistic density inversions that could lead to numerical instabilities in ocean models. Uses the UNESCO 1983 equation of state to verify hydrostatic stability.

### 2. Steric Height Constraint
Constrains sea surface height (SSH) increments derived from temperature and salinity changes to remain within physically meaningful limits.

### 3. Hard Bounds Enforcement
Brute-force check to ensure analysis values of temperature and salinity remain within defined minimum and maximum values.

## Directory Structure

```
gdas_incr_qc_standalone/
├── README.md                           # This file
├── CMakeLists.txt                      # CMake build configuration
├── include/
│   └── gdas_incr_qc/
│       ├── gdas_incr_qc.h             # Main QC interface
│       ├── gdas_incr_qc_utils.h       # QC utility functions
│       ├── gdas_soca_utils.h          # SOCA utilities (density, steric height)
│       └── gdas_soca_diagb_utils.h    # Mesh connectivity utilities
├── doc/
│   └── README.md                       # Detailed documentation
└── examples/
    └── example_usage.cc                # Example usage (to be created)
```

## Dependencies

This library requires the following external dependencies:

### Required
- **ATLAS** - ECMWF library for handling unstructured meshes and field operations
- **OOPS** - Object-Oriented Prediction System framework
- **SOCA** - Sea-Ocean-Cryosphere-Atmosphere data assimilation system
- **eckit** - ECMWF toolkit for configuration and utilities
- **C++11 or later**

## Installation

### Using CMake

```bash
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/path/to/install ..
make
make install
```

### Integration into Existing Project

Since this is a header-only library, you can simply:

1. Copy the `include/gdas_incr_qc/` directory to your project
2. Add the include path to your compiler flags:
   ```cmake
   target_include_directories(your_target PRIVATE /path/to/gdas_incr_qc_standalone/include)
   ```
3. Link against required dependencies (ATLAS, OOPS, SOCA, eckit)

## Usage

```cpp
#include <gdas_incr_qc/gdas_incr_qc.h>

// In your code:
soca::State xb;         // Background state
soca::Increment dx;     // Increment to QC
soca::Geometry geom;    // Geometry
eckit::Configuration config;  // QC configuration

// Perform QC on the increment (modifies dx in place)
gdasapp::incrqc::qcIncrement(xb, dx, config, geom);
```

## Configuration

The QC requires the following configuration parameters:

```yaml
state bounds:
  sea_water_potential_temperature: [-2.0, 40.0]  # [°C]
  sea_water_salinity: [0.0, 50.0]                # [psu]

increment max:
  steric: 0.5  # Maximum allowed steric height increment [m]

increment stability iterations: 10
increment smoothing iterations: 30
min stable density gradient: 1.0e-4  # [kg/m³/m]

steric increment:
  linear variable changes:
  - linear variable change name: BalanceSOCA
```

## Documentation

See `doc/README.md` for detailed documentation including:
- Mathematical formulation of the stability check
- Algorithm descriptions
- Configuration parameters
- References

## License

This library is extracted from GDASApp, which is maintained by NOAA-EMC.
Please refer to the original repository for licensing information:
https://github.com/NOAA-EMC/GDASApp

## References

- Fofonoff, N. P., & Millard, R. C. (1983). Algorithms for computation of fundamental properties of seawater. UNESCO technical papers in marine science, 44, 53.
- Pedlosky, J. (1987). *Geophysical Fluid Dynamics*. Springer.
- Lellouche, J.-M. et al. (2018). Recent updates to the Copernicus Marine Service global ocean... *Ocean Sci.*, 14, 1093–1126.

## Contributing

This is a standalone extraction from GDASApp. For contributions to the main project, please visit:
https://github.com/NOAA-EMC/GDASApp

## Contact

For questions about this standalone library, please open an issue in your repository or contact the GDASApp development team.

## Acknowledgments

Extracted from the Global Data Assimilation System Application (GDASApp) developed by NOAA-EMC.
