list( APPEND gdas_provider2ioda_src_files
	obsprovider2ioda.cc
	obsprovider2ioda.h
)

if(CMAKE_PROJECT_NAME)
    set(target_name "${CMAKE_PROJECT_NAME}_obsprovider2ioda.x)
else()
    set(target_name "obsprovider2ioda.x")
endif()

ecbuild_add_executable( TARGET ${target_name}
                        SOURCES ${gdas_provider2ioda_src_files} )

target_compile_features( ${target_name} PUBLIC cxx_std_17)

target_link_libraries( ${target_name} PUBLIC oops ioda netcdf2ioda NetCDF::NetCDF_CXX)

# Set the RPATH to the build directory
set_target_properties(${target_name} PROPERTIES
    BUILD_WITH_INSTALL_RPATH TRUE
    INSTALL_RPATH "${CMAKE_BINARY_DIR}/lib"
    INSTALL_RPATH_USE_LINK_PATH TRUE
)
