cmake_minimum_required(VERSION 3.12)
project(gdas_incr_qc VERSION 1.0.0 LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(BUILD_EXAMPLES "Build example programs" OFF)
option(BUILD_TESTING "Build tests" OFF)

# Find required dependencies
# Note: These are required external dependencies from the JEDI ecosystem
find_package(eckit REQUIRED)
find_package(atlas REQUIRED)
find_package(oops REQUIRED)
find_package(soca REQUIRED)

# Create interface library (header-only)
add_library(gdas_incr_qc INTERFACE)

# Set include directories
target_include_directories(gdas_incr_qc INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# Link dependencies
target_link_libraries(gdas_incr_qc INTERFACE
    eckit
    atlas
    oops
    soca
)

# Installation
include(GNUInstallDirs)

install(TARGETS gdas_incr_qc
    EXPORT gdas_incr_qc-targets
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(DIRECTORY include/gdas_incr_qc
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
    FILES_MATCHING PATTERN "*.h"
)

install(FILES doc/README.md
    DESTINATION ${CMAKE_INSTALL_DOCDIR}
)

# Export targets
install(EXPORT gdas_incr_qc-targets
    FILE gdas_incr_qc-targets.cmake
    NAMESPACE gdas_incr_qc::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/gdas_incr_qc
)

# Create package config file
include(CMakePackageConfigHelpers)

configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/gdas_incr_qc-config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/gdas_incr_qc-config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/gdas_incr_qc
)

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/gdas_incr_qc-config-version.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/gdas_incr_qc-config.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/gdas_incr_qc-config-version.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/gdas_incr_qc
)

# Examples (optional)
if(BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()

# Testing (optional)
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(test)
endif()

# Print summary
message(STATUS "")
message(STATUS "========================================")
message(STATUS "GDAS Increment QC Configuration Summary")
message(STATUS "========================================")
message(STATUS "  Version: ${PROJECT_VERSION}")
message(STATUS "  C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  Build examples: ${BUILD_EXAMPLES}")
message(STATUS "  Build testing: ${BUILD_TESTING}")
message(STATUS "  Install prefix: ${CMAKE_INSTALL_PREFIX}")
message(STATUS "========================================")
message(STATUS "")
