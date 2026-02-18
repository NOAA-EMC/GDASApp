#!/bin/bash
# verify_extraction.sh - Verify the standalone extraction is complete

set -e

echo "================================================"
echo "GDAS Increment QC - Extraction Verification"
echo "================================================"
echo ""

# Check directory structure
echo "Checking directory structure..."
REQUIRED_DIRS=(
    "include/gdas_incr_qc"
    "doc"
    "cmake"
    "examples"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir exists"
    else
        echo "  ✗ $dir missing"
        exit 1
    fi
done
echo ""

# Check required files
echo "Checking required files..."
REQUIRED_FILES=(
    "README.md"
    "DEPENDENCIES.md"
    "MANIFEST.md"
    "LICENSE"
    "CMakeLists.txt"
    "cmake/gdas_incr_qc-config.cmake.in"
    "include/gdas_incr_qc/gdas_incr_qc.h"
    "include/gdas_incr_qc/gdas_incr_qc_utils.h"
    "include/gdas_incr_qc/gdas_soca_utils.h"
    "include/gdas_incr_qc/gdas_soca_diagb_utils.h"
    "doc/README.md"
    "examples/example_usage.cc"
    "examples/CMakeLists.txt"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file missing"
        exit 1
    fi
done
echo ""

# Check header file syntax (basic check)
echo "Checking header files..."
for header in include/gdas_incr_qc/*.h; do
    if grep -q "^#pragma once" "$header" || grep -q "^#ifndef.*_H" "$header"; then
        echo "  ✓ $(basename $header) has include guard"
    else
        echo "  ✗ $(basename $header) missing include guard"
    fi
done
echo ""

# Check for correct namespace usage
echo "Checking namespace structure..."
if grep -r "namespace gdasapp" include/gdas_incr_qc/*.h > /dev/null; then
    echo "  ✓ gdasapp namespace found"
else
    echo "  ✗ gdasapp namespace not found"
    exit 1
fi

if grep -r "namespace incrqc" include/gdas_incr_qc/gdas_incr_qc*.h > /dev/null; then
    echo "  ✓ incrqc namespace found"
else
    echo "  ✗ incrqc namespace not found"
    exit 1
fi
echo ""

# Check for key functions
echo "Checking key functions..."
KEY_FUNCTIONS=(
    "qcIncrement"
    "applyWaterColumnStabilityCheck"
    "applyStericHeightConstraint"
    "applyBruteForceBoundsCheck"
    "computeDensityUNESCO"
    "computeStericHeightIncrement"
    "buildMeshConnectivity"
)

for func in "${KEY_FUNCTIONS[@]}"; do
    if grep -r "$func" include/gdas_incr_qc/*.h > /dev/null; then
        echo "  ✓ $func found"
    else
        echo "  ✗ $func not found"
        exit 1
    fi
done
echo ""

# Check include paths have been updated
echo "Checking include paths..."
if grep -r '\.\./diagb/' include/gdas_incr_qc/*.h > /dev/null; then
    echo "  ✗ Old relative paths still present (../diagb/)"
    exit 1
else
    echo "  ✓ No old relative paths found"
fi

if grep -r '\.\./gdas_soca_utils\.h' include/gdas_incr_qc/*.h > /dev/null; then
    echo "  ✗ Old relative paths still present (../gdas_soca_utils.h)"
    exit 1
else
    echo "  ✓ No old relative paths found"
fi
echo ""

# File count summary
echo "File count summary:"
echo "  Header files: $(find include/gdas_incr_qc -name "*.h" | wc -l)"
echo "  Documentation files: $(find doc -name "*.md" | wc -l)"
echo "  Example files: $(find examples -name "*.cc" | wc -l)"
echo "  CMake files: $(find . -name "CMakeLists.txt" | wc -l)"
echo ""

# Size check
echo "Size summary:"
TOTAL_SIZE=$(du -sh . | cut -f1)
echo "  Total size: $TOTAL_SIZE"
echo ""

echo "================================================"
echo "✓ All verification checks passed!"
echo "================================================"
echo ""
echo "Next steps:"
echo "  1. Review the extracted files"
echo "  2. Copy this directory to your new repository"
echo "  3. Install dependencies (see DEPENDENCIES.md)"
echo "  4. Build with CMake:"
echo "     mkdir build && cd build"
echo "     cmake .."
echo "     make"
echo ""
