# GDAS Increment QC - Quick Start Guide

This guide will help you quickly get started with the extracted standalone library.

## What You Have

A complete, self-contained extraction of the GDAS increment quality control library:

- **4 header files** with all QC functionality
- **Complete documentation** (technical and user guides)
- **CMake build system** for easy integration
- **Example code** showing usage
- **Verification script** to check extraction integrity

## Immediate Next Steps

### 1. Verify the Extraction

```bash
cd gdas_incr_qc_standalone
./verify_extraction.sh
```

This will check that all files are present and correctly structured.

### 2. Review the Documentation

Start with these files in this order:

1. **`README.md`** (this directory) - Overview and features
2. **`MANIFEST.md`** - What was extracted and from where
3. **`DEPENDENCIES.md`** - How to install dependencies
4. **`doc/README.md`** - Detailed technical documentation

### 3. Understand the Dependencies

This library requires the JEDI ecosystem components:
- **eckit** - Configuration management
- **ATLAS** - Mesh and field operations
- **OOPS** - Data assimilation framework
- **SOCA** - Ocean DA components

See `DEPENDENCIES.md` for installation instructions.

## Integration Options

### Option A: Copy to New Repository (Recommended)

```bash
# Copy the entire directory to your new repository
cp -r gdas_incr_qc_standalone /path/to/your/new/repo/

# Initialize git if needed
cd /path/to/your/new/repo/gdas_incr_qc_standalone
git init
git add .
git commit -m "Initial import of GDAS increment QC library"
```

### Option B: Use as Git Submodule

```bash
# In your project repository
git submodule add <url-to-your-gdas-incr-qc-repo> external/gdas_incr_qc

# In your CMakeLists.txt:
add_subdirectory(external/gdas_incr_qc)
target_link_libraries(your_app PRIVATE gdas_incr_qc::gdas_incr_qc)
```

### Option C: Install System-Wide

```bash
cd gdas_incr_qc_standalone
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
make
sudo make install

# Then in your project:
find_package(gdas_incr_qc REQUIRED)
target_link_libraries(your_app PRIVATE gdas_incr_qc::gdas_incr_qc)
```

## Building the Library

### Prerequisites

1. C++11 or later compiler
2. CMake 3.12 or later
3. JEDI dependencies installed (eckit, atlas, oops, soca)

### Build Commands

```bash
cd gdas_incr_qc_standalone
mkdir build && cd build

# Configure
cmake .. \
  -DCMAKE_PREFIX_PATH="/path/to/jedi/install" \
  -DCMAKE_INSTALL_PREFIX="/path/to/install" \
  -DBUILD_EXAMPLES=ON

# Build
make -j4

# Install (optional)
make install
```

## Testing the Integration

### Quick Test: Check Headers

```bash
# Create a simple test file
cat > test_include.cc << 'EOF'
#include <gdas_incr_qc/gdas_incr_qc.h>
int main() {
    // Just test that headers compile
    return 0;
}
EOF

# Try to compile (adjust paths as needed)
g++ -std=c++11 \
    -I./include \
    -I/path/to/eckit/include \
    -I/path/to/atlas/include \
    -I/path/to/oops/include \
    -I/path/to/soca/include \
    test_include.cc -c
```

### Full Test: Build Example

```bash
cd build
make example_usage
./examples/example_usage
```

## Using in Your Code

### Minimal Example

```cpp
#include <gdas_incr_qc/gdas_incr_qc.h>

void qc_my_increment(soca::State& xb,
                     soca::Increment& dx,
                     const soca::Geometry& geom) {

    // Configure QC parameters
    eckit::LocalConfiguration qcConfig;
    qcConfig.set("state bounds.sea_water_potential_temperature",
                 std::vector<double>{-2.0, 40.0});
    qcConfig.set("state bounds.sea_water_salinity",
                 std::vector<double>{0.0, 50.0});
    qcConfig.set("increment max.steric", 0.5);
    qcConfig.set("increment stability iterations", 10);
    qcConfig.set("min stable density gradient", 1.0e-4);

    // Apply QC (modifies dx in place)
    gdasapp::incrqc::qcIncrement(xb, dx, qcConfig, geom);
}
```

## File Overview

### Headers (include/gdas_incr_qc/)

- **`gdas_incr_qc.h`** - Main interface with `qcIncrement()` function
- **`gdas_incr_qc_utils.h`** - QC utility functions (stability, bounds, etc.)
- **`gdas_soca_utils.h`** - Ocean utilities (density, steric height)
- **`gdas_soca_diagb_utils.h`** - Mesh and connectivity utilities

### Key Functions

```cpp
// Main QC entry point
void gdasapp::incrqc::qcIncrement(
    const soca::State& xb,      // Background state
    soca::Increment& dx,         // Increment to QC (modified in place)
    const eckit::Configuration& config,  // QC parameters
    const soca::Geometry& geom); // Geometry

// Individual QC operations (called internally)
void applyWaterColumnStabilityCheck(...);
void applyStericHeightConstraint(...);
void applyBruteForceBoundsCheck(...);

// Utility functions
double computeDensityUNESCO(double temp, double salt);
double computeStericHeightIncrement(...);
```

## Common Issues

### Issue: "Cannot find package eckit/atlas/oops/soca"

**Solution**: Set `CMAKE_PREFIX_PATH` to include all JEDI install locations:
```bash
export CMAKE_PREFIX_PATH="/path/to/jedi/install:$CMAKE_PREFIX_PATH"
```

### Issue: "Header not found"

**Solution**: Make sure you're including the correct path:
```cpp
#include <gdas_incr_qc/gdas_incr_qc.h>  // Correct
#include "gdas_incr_qc.h"                // Wrong
```

### Issue: Link errors with SOCA/OOPS

**Solution**: Ensure all libraries are built with the same compiler and linked in the correct order:
```cmake
target_link_libraries(your_app PRIVATE
    gdas_incr_qc::gdas_incr_qc
    soca
    oops
    atlas
    eckit
)
```

## Getting Help

1. **Technical Documentation**: See `doc/README.md` for algorithm details
2. **Dependencies**: See `DEPENDENCIES.md` for installation help
3. **File Origins**: See `MANIFEST.md` for source file mapping
4. **Examples**: See `examples/example_usage.cc` for usage patterns

## What's Included

✓ All QC algorithms (water column stability, steric height, bounds)
✓ Complete mathematical formulations
✓ Mesh connectivity utilities
✓ Ocean utilities (density, steric height calculations)
✓ CMake build system
✓ Documentation and examples
✓ Verification tools

## What's NOT Included

✗ JEDI dependencies (must install separately)
✗ Test data files
✗ Integration tests (can be adapted from GDASApp)
✗ Python bindings (C++ only)

## Maintenance

To keep your standalone library updated with GDASApp changes:

```bash
# In the original GDASApp repository
cd /path/to/GDASApp
git pull origin develop

# Check for changes in source files
git log --since="2024-01-01" -- utils/soca/incrqc/
git log --since="2024-01-01" -- utils/soca/gdas_soca_utils.h
git log --since="2024-01-01" -- utils/soca/diagb/gdas_soca_diagb_utils.h

# If there are updates, manually apply them to your standalone copy
```

## Success Criteria

You're ready to use the library when:

- ✓ Verification script passes
- ✓ Dependencies are installed
- ✓ Example code compiles
- ✓ Headers can be included in your project
- ✓ You understand the QC configuration parameters

## Next Steps

1. **Copy to your repository**: `cp -r gdas_incr_qc_standalone /path/to/your/repo/`
2. **Install dependencies**: Follow `DEPENDENCIES.md`
3. **Integrate into your build**: Add to your CMakeLists.txt
4. **Configure QC parameters**: Set up config YAML/dictionary
5. **Test with your data**: Run on actual ocean increments

## Questions?

- Review the detailed documentation in `doc/README.md`
- Check the original GDASApp repository: https://github.com/NOAA-EMC/GDASApp
- See JEDI documentation: https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/

---

**Ready to port?** Just copy the entire `gdas_incr_qc_standalone` directory to your new repository!
