# GDAS Increment QC - Dependencies and Integration Guide

## External Dependencies

This library depends on several components from the JEDI (Joint Effort for Data assimilation Integration) ecosystem developed by JCSDA (Joint Center for Satellite Data Assimilation).

### Core Dependencies

#### 1. **eckit** (ECMWF Toolkit)
- **Purpose**: Configuration management, utilities
- **Repository**: https://github.com/ecmwf/eckit
- **License**: Apache License 2.0
- **Installation**:
  ```bash
  git clone https://github.com/ecmwf/eckit.git
  cd eckit
  mkdir build && cd build
  cmake -DCMAKE_INSTALL_PREFIX=/path/to/install ..
  make -j4
  make install
  ```

#### 2. **ATLAS** (A library for numerical weather prediction and climate modelling)
- **Purpose**: Unstructured mesh handling, field operations, parallel computations
- **Repository**: https://github.com/ecmwf-ifs/atlas
- **License**: Apache License 2.0
- **Installation**:
  ```bash
  git clone https://github.com/ecmwf-ifs/atlas.git
  cd atlas
  mkdir build && cd build
  cmake -DCMAKE_INSTALL_PREFIX=/path/to/install ..
  make -j4
  make install
  ```

#### 3. **OOPS** (Object-Oriented Prediction System)
- **Purpose**: Generic data assimilation framework
- **Repository**: https://github.com/JCSDA/oops
- **License**: Apache License 2.0
- **Installation**:
  ```bash
  git clone https://github.com/JCSDA/oops.git
  cd oops
  mkdir build && cd build
  cmake -DCMAKE_INSTALL_PREFIX=/path/to/install ..
  make -j4
  make install
  ```

#### 4. **SOCA** (Sea-Ocean-Cryosphere-Atmosphere DA)
- **Purpose**: Ocean-specific DA components (State, Increment, Geometry, LinearVariableChange)
- **Repository**: https://github.com/JCSDA-internal/soca
- **License**: Apache License 2.0
- **Note**: May require JCSDA membership access
- **Installation**:
  ```bash
  git clone https://github.com/JCSDA-internal/soca.git
  cd soca
  mkdir build && cd build
  cmake -DCMAKE_INSTALL_PREFIX=/path/to/install ..
  make -j4
  make install
  ```

### Dependency Tree

```
gdas_incr_qc
├── eckit (configuration, utilities)
├── atlas (mesh operations, fields, parallel)
│   └── eckit
├── oops (DA framework, Logger, DateTime, Variables)
│   └── eckit
└── soca (ocean DA, State, Increment, Geometry)
    ├── oops
    ├── atlas
    └── eckit
```

## Building with Dependencies

### Option 1: Using JEDI Ecosystem Build System

The easiest way to build this library is within the JEDI ecosystem using the bundle system:

```bash
# Clone the JEDI bundle (contains all dependencies)
git clone https://github.com/JCSDA/jedi-bundle.git
cd jedi-bundle

# Add gdas_incr_qc as a bundle component
# Edit CMakeLists.txt to add:
# ecbuild_bundle( PROJECT gdas_incr_qc GIT "/path/to/gdas_incr_qc_standalone" )

# Build the bundle
mkdir build && cd build
ecbuild ..
make -j4
```

### Option 2: Manual Build with Pre-installed Dependencies

If you have already installed the dependencies:

```bash
cd gdas_incr_qc_standalone
mkdir build && cd build

cmake .. \
  -DCMAKE_PREFIX_PATH="/path/to/eckit;/path/to/atlas;/path/to/oops;/path/to/soca" \
  -DCMAKE_INSTALL_PREFIX=/path/to/install

make
make install
```

### Option 3: Using Environment Modules

Many HPC systems provide JEDI dependencies via modules:

```bash
module load jedi/1.0.0  # or similar
cd gdas_incr_qc_standalone
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/path/to/install ..
make
make install
```

## Using the Library in Your Project

### CMake Integration

```cmake
# In your CMakeLists.txt
find_package(gdas_incr_qc REQUIRED)

add_executable(your_app main.cc)
target_link_libraries(your_app PRIVATE gdas_incr_qc::gdas_incr_qc)
```

### Manual Integration

If not using CMake:

```bash
# Compilation
g++ -std=c++11 \
    -I/path/to/gdas_incr_qc/include \
    -I/path/to/eckit/include \
    -I/path/to/atlas/include \
    -I/path/to/oops/include \
    -I/path/to/soca/include \
    your_code.cc \
    -L/path/to/libs \
    -leckit -latlas -loops -lsoca \
    -o your_app
```

## Porting to a New Environment

When porting this library to a new environment or repository:

1. **Copy the entire `gdas_incr_qc_standalone/` directory** to your new location

2. **Install dependencies** (follow instructions above for each dependency)

3. **Verify dependencies** are findable by CMake:
   ```bash
   cmake --find-package -DNAME=eckit -DCOMPILER_ID=GNU -DLANGUAGE=CXX -DMODE=EXIST
   cmake --find-package -DNAME=atlas -DCOMPILER_ID=GNU -DLANGUAGE=CXX -DMODE=EXIST
   cmake --find-package -DNAME=oops -DCOMPILER_ID=GNU -DLANGUAGE=CXX -DMODE=EXIST
   cmake --find-package -DNAME=soca -DCOMPILER_ID=GNU -DLANGUAGE=CXX -DMODE=EXIST
   ```

4. **Build and test**:
   ```bash
   cd gdas_incr_qc_standalone
   mkdir build && cd build
   cmake .. -DBUILD_EXAMPLES=ON -DBUILD_TESTING=ON
   make
   ctest
   ```

## Minimal Working Example

```cpp
#include <gdas_incr_qc/gdas_incr_qc.h>

int main() {
    // Initialize SOCA geometry, state, and increment
    // (requires proper configuration files)

    soca::Geometry geom(geomConfig);
    soca::State xb(geom, stateConfig);
    soca::Increment dx(geom, xb.variables(), xb.validTime());

    // Set up QC configuration
    eckit::LocalConfiguration qcConfig;
    qcConfig.set("state bounds.sea_water_potential_temperature", std::vector<double>{-2.0, 40.0});
    qcConfig.set("state bounds.sea_water_salinity", std::vector<double>{0.0, 50.0});
    qcConfig.set("increment max.steric", 0.5);
    qcConfig.set("increment stability iterations", 10);
    qcConfig.set("min stable density gradient", 1.0e-4);

    // Apply QC
    gdasapp::incrqc::qcIncrement(xb, dx, qcConfig, geom);

    return 0;
}
```

## Troubleshooting

### Common Issues

1. **Cannot find dependencies**
   - Set `CMAKE_PREFIX_PATH` to include all dependency installation paths
   - Use `find_package(XXX REQUIRED)` with `PATHS` hint

2. **Version mismatches**
   - Ensure all JEDI components are from compatible versions
   - Use the same compiler for all components

3. **Missing symbols at link time**
   - Verify all dependencies are linked in correct order
   - Check that shared libraries are in `LD_LIBRARY_PATH`

## Support

For issues with:
- **Dependencies (eckit, atlas)**: See ECMWF repositories
- **JEDI components (oops, soca)**: See JCSDA repositories
- **This library**: Contact your local maintainer or check the original GDASApp repository

## Additional Resources

- JEDI Documentation: https://jointcenterforsatellitedataassimilation-jedi-docs.readthedocs-hosted.com/
- JCSDA GitHub: https://github.com/JCSDA
- GDASApp: https://github.com/NOAA-EMC/GDASApp
