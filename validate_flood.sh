#!/bin/bash

# Simple validation script for Flood class implementation
# Tests basic file structure and includes

echo "=== Flood Class Implementation Validation ==="

echo "1. Checking if Flood.h exists..."
if [ -f "mains/Flood.h" ]; then
    echo "✓ Flood.h found"
else
    echo "✗ Flood.h not found"
    exit 1
fi

echo "2. Checking if Flood.cc exists..."
if [ -f "mains/Flood.cc" ]; then
    echo "✓ Flood.cc found"
else
    echo "✗ Flood.cc not found"
    exit 1
fi

echo "3. Checking Flood class namespace..."
if grep -q "namespace gdas" mains/Flood.h && grep -q "namespace gdas" mains/Flood.cc; then
    echo "✓ gdas namespace found in both files"
else
    echo "✗ gdas namespace missing"
    exit 1
fi

echo "4. Checking template class definition..."
if grep -q "template.*class Flood.*public oops::Application" mains/Flood.h; then
    echo "✓ Template class definition correct"
else
    echo "✗ Template class definition missing or incorrect"
    exit 1
fi

echo "5. Checking CMakeLists.txt includes Flood.cc..."
if grep -q "Flood.cc" mains/CMakeLists.txt; then
    echo "✓ CMakeLists.txt updated"
else
    echo "✗ CMakeLists.txt not updated"
    exit 1
fi

echo "6. Checking gdas.cc includes flood application..."
if grep -q "flood" mains/gdas.cc && grep -q "gdas::Flood" mains/gdas.cc; then
    echo "✓ gdas.cc updated with flood application"
else
    echo "✗ gdas.cc not properly updated"
    exit 1
fi

echo "=== All validations passed! ==="
exit 0