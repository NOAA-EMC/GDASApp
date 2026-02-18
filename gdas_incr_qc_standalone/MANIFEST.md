# GDAS Increment QC - Standalone Library
# File Manifest and Extraction Information

## Extraction Date
Generated from GDASApp repository on: $(date)

## Source Repository
- **Original Repository**: https://github.com/NOAA-EMC/GDASApp
- **Branch**: develop
- **Extracted Components**: utils/soca/incrqc and dependencies

## File Listing

### Core Library Headers
```
include/gdas_incr_qc/
├── gdas_incr_qc.h              # Main QC interface (from utils/soca/incrqc/)
├── gdas_incr_qc_utils.h        # QC utility functions (from utils/soca/incrqc/)
├── gdas_soca_utils.h           # SOCA utilities (from utils/soca/)
└── gdas_soca_diagb_utils.h     # Mesh connectivity (from utils/soca/diagb/)
```

### Documentation
```
doc/
└── README.md                   # Detailed documentation (from utils/soca/incrqc/)

README.md                       # Main readme (created)
DEPENDENCIES.md                 # Dependency guide (created)
MANIFEST.md                     # This file (created)
LICENSE                         # LGPL 2.1 (from root)
```

### Build System
```
CMakeLists.txt                  # Main CMake config (created)
cmake/
└── gdas_incr_qc-config.cmake.in  # Package config template (created)
```

### Examples
```
examples/
├── CMakeLists.txt              # Examples build config (created)
└── example_usage.cc            # Usage example (created)
```

## Source File Origins

| Standalone File | Original GDASApp Location |
|----------------|---------------------------|
| `include/gdas_incr_qc/gdas_incr_qc.h` | `utils/soca/incrqc/gdas_incr_qc.h` |
| `include/gdas_incr_qc/gdas_incr_qc_utils.h` | `utils/soca/incrqc/gdas_incr_qc_utils.h` |
| `include/gdas_incr_qc/gdas_soca_utils.h` | `utils/soca/gdas_soca_utils.h` |
| `include/gdas_incr_qc/gdas_soca_diagb_utils.h` | `utils/soca/diagb/gdas_soca_diagb_utils.h` |
| `doc/README.md` | `utils/soca/incrqc/README.md` |
| `LICENSE` | `LICENSE` |

## Changes Made for Standalone Distribution

1. **Include Path Updates**:
   - Modified relative includes in headers to use consistent paths
   - Changed `#include "../diagb/gdas_soca_diagb_utils.h"` to `#include "gdas_soca_diagb_utils.h"`
   - Changed `#include "../gdas_soca_utils.h"` to `#include "gdas_soca_utils.h"`

2. **Created New Files**:
   - `README.md` - Overview and quick start guide
   - `DEPENDENCIES.md` - Detailed dependency installation guide
   - `CMakeLists.txt` - CMake build configuration
   - `cmake/gdas_incr_qc-config.cmake.in` - Package configuration
   - `examples/example_usage.cc` - Usage example
   - `examples/CMakeLists.txt` - Example build config
   - `MANIFEST.md` - This file

3. **No Changes to Core Logic**:
   - All QC algorithms remain unchanged
   - Function signatures are identical
   - Mathematical formulations preserved

## Dependencies

### External (Required)
- eckit (ECMWF toolkit)
- ATLAS (mesh and field operations)
- OOPS (DA framework)
- SOCA (ocean DA)

### C++ Standard
- C++11 or later

## Component Descriptions

### gdas_incr_qc.h
Main interface for increment quality control. Provides:
- `qcIncrement()` - Main QC function

### gdas_incr_qc_utils.h
Utility functions for QC operations:
- `adjustAnalysisBounds()` - Enforce scalar bounds
- `applyWaterColumnStabilityCheck()` - Check density stability
- `applyStericHeightConstraint()` - Limit SSH increments
- `applyBruteForceBoundsCheck()` - Hard bounds enforcement

### gdas_soca_utils.h
SOCA utility functions:
- `computeDensityUNESCO()` - UNESCO 1983 density equation
- `computeStericHeightIncrement()` - Steric height calculations
- `computeDepthAndBathymetry()` - Depth/bathymetry from thickness

### gdas_soca_diagb_utils.h
Mesh connectivity and diagnostic utilities:
- `MeshBundle` - Atlas mesh wrapper
- `buildMeshConnectivity()` - Build mesh edges and halos
- `get_neighbors_of_node()` - Find neighboring nodes
- `computeLocalGCScale()` - Gaspari-Cohn e-folding
- `localMean()` - Local averaging over depth bins

## Testing

The original GDASApp repository contains tests for this functionality in:
- `test/soca/` (various ocean DA tests)

Tests were not extracted but can be adapted from the original repository.

## Maintenance

To sync with upstream GDASApp changes:

1. Check for updates in source files:
   ```bash
   cd /path/to/GDASApp
   git pull origin develop
   git log --follow -- utils/soca/incrqc/
   git log --follow -- utils/soca/gdas_soca_utils.h
   git log --follow -- utils/soca/diagb/gdas_soca_diagb_utils.h
   ```

2. Apply changes to standalone library
3. Test with your application
4. Update version in CMakeLists.txt

## Version History

- **v1.0.0** (Initial extraction)
  - Extracted from GDASApp develop branch
  - Created standalone build system
  - Added documentation and examples

## Contact and Support

For issues related to:
- **Standalone library structure**: Contact your local maintainer
- **QC algorithms**: Refer to GDASApp issues
- **JEDI dependencies**: See JCSDA documentation

## Acknowledgments

This standalone extraction includes code developed by NOAA-EMC as part of the
Global Data Assimilation System Application (GDASApp).

Original authors and contributors can be found in the GDASApp repository:
https://github.com/NOAA-EMC/GDASApp/graphs/contributors
