# Define the library target
add_library(netcdf2ioda
    IcecAmsr2Ioda.h
    IcecAbi2Ioda.h
    Ghrsst2Ioda.h
    Viirsaod2Ioda.h
    util.h
    superob.h
    Smos2Ioda.h
    Smap2Ioda.h
    Rads2Ioda.h
    NetCDFToIodaConverter.h
    InsituAll2ioda.h
    IcecMirs2Ioda.h
    IcecJpssrr2Ioda.h
    Tmsrad2Ioda.h
    rtofs/util.h
    rtofs/RTOFSOb.h
    rtofs/RTOFSOb.cc
    rtofs/RTOFSDataFile.h
    rtofs/README
    rtofs/CMakeLists.txt
    rtofs/util.cc
    rtofs/RTOFSDataFile.cc
)

# Specify include directories
target_include_directories(netcdf2ioda PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Specify the linker language
set_target_properties(netcdf2ioda PROPERTIES LINKER_LANGUAGE CXX)

# Set the output directory for the library
set_target_properties(netcdf2ioda PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
)

# Include oops headers
target_include_directories(netcdf2ioda PUBLIC ${OOPS_INCLUDE_DIRS})

# Link the oops library
target_link_libraries(netcdf2ioda PUBLIC oops ioda)

add_subdirectory(applications)
