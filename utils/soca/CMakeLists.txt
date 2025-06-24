# Set the output directory for libraries
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# Diagnostic Library
add_library(gdas_soca_diagnostics SHARED diagnostics/gdas_soca_diagnostics.cc)
target_include_directories(gdas_soca_diagnostics PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/diagnostics)
target_link_libraries(gdas_soca_diagnostics PUBLIC atlas oops soca)
set_target_properties(gdas_soca_diagnostics PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${CMAKE_LIBRARY_OUTPUT_DIRECTORY})

# Increment post processing
ecbuild_add_executable( TARGET gdas_incr_handler.x
                        SOURCES gdas_incr_handler.cc)
target_compile_features( gdas_incr_handler.x PUBLIC cxx_std_11)
target_include_directories(gdas_incr_handler.x PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/incrqc)
target_link_libraries( gdas_incr_handler.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca gdas_soca_diagnostics)
target_link_libraries( gdas_incr_handler.x PRIVATE stdc++fs)

# Ensemble members post processing
ecbuild_add_executable( TARGET gdas_ens_handler.x
                        SOURCES gdas_ens_handler.cc gdas_postprocincr.h)
target_compile_features( gdas_ens_handler.x PUBLIC cxx_std_11)
target_link_libraries( gdas_ens_handler.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca gdas_soca_diagnostics)
target_link_libraries( gdas_ens_handler.x PRIVATE stdc++fs)

# Hybrid-Weight
ecbuild_add_executable( TARGET gdas_socahybridweights.x
                        SOURCES gdas_socahybridweights.cc )
target_compile_features( gdas_socahybridweights.x PUBLIC cxx_std_17)
target_link_libraries( gdas_socahybridweights.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca)

# Obs Stats
ecbuild_add_executable( TARGET gdassoca_obsstats.x
                        SOURCES gdassoca_obsstats.cc )
target_compile_features( gdassoca_obsstats.x PUBLIC cxx_std_17)
target_link_libraries( gdassoca_obsstats.x PUBLIC NetCDF::NetCDF_CXX oops ioda)

# Diag B
add_subdirectory( diagb )

# Testing
add_subdirectory( test )