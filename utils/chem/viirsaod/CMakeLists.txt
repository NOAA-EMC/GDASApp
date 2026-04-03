# Define the library target
add_library(netcdf2ioda
    Viirsaod2Ioda.h
    util.h
    superob.h
    NetCDFToIodaConverter.h
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

install(TARGETS netcdf2ioda
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib
  RUNTIME DESTINATION bin
)

add_subdirectory(applications)
