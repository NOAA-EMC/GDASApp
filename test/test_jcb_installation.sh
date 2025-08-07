#!/bin/bash

# Test script to verify that jcb is properly installed during build
# This script should be run after a successful CMake build

set -e

echo "Testing jcb installation in build directory..."

# Get the build directory - assuming it's passed as first argument or use default
BUILD_DIR="${1:-${CMAKE_INSTALL_PREFIX:-./install}}"

if [ ! -d "$BUILD_DIR" ]; then
    echo "Error: Build directory '$BUILD_DIR' does not exist"
    exit 1
fi

echo "Using build directory: $BUILD_DIR"

# Find the Python site-packages directory
PYTHON_SITE_PACKAGES=$(find "$BUILD_DIR" -path "*/lib/python*/dist-packages" -o -path "*/lib/python*/site-packages" | head -1)
if [ -z "$PYTHON_SITE_PACKAGES" ]; then
    echo "Error: Could not find Python site-packages directory in $BUILD_DIR"
    exit 1
fi

# Find the bin directory
BIN_DIR=$(find "$BUILD_DIR" -name "bin" -type d | head -1)
if [ -z "$BIN_DIR" ]; then
    echo "Error: Could not find bin directory in $BUILD_DIR"
    exit 1
fi

echo "Python packages directory: $PYTHON_SITE_PACKAGES"
echo "Binary directory: $BIN_DIR"

# Check if jcb package is installed
if [ ! -d "$PYTHON_SITE_PACKAGES/jcb" ]; then
    echo "Error: jcb Python package not found in $PYTHON_SITE_PACKAGES"
    exit 1
fi

# Check if jcb command is available
if [ ! -f "$BIN_DIR/jcb" ]; then
    echo "Error: jcb command not found in $BIN_DIR"
    exit 1
fi

# Test if jcb command works
export PYTHONPATH="$PYTHON_SITE_PACKAGES:$PYTHONPATH"  
export PATH="$BIN_DIR:$PATH"

echo "Testing jcb command..."
if ! jcb --version; then
    echo "Error: jcb command failed to run"
    exit 1
fi

echo "✓ jcb is properly installed and functional"
echo "✓ jcb command is available at: $BIN_DIR/jcb"
echo "✓ jcb package is installed at: $PYTHON_SITE_PACKAGES/jcb"

exit 0
