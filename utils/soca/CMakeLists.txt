        # Set the output directory for libraries
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# Diagnostic Library
add_library(gdas_soca_diagnostics SHARED diagnostics/Diagnostics.cc)
target_include_directories(gdas_soca_diagnostics PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/diagnostics)
target_link_libraries(gdas_soca_diagnostics PUBLIC atlas oops soca)
set_target_properties(gdas_soca_diagnostics PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${CMAKE_LIBRARY_OUTPUT_DIRECTORY})

# Diagnostics
ecbuild_add_executable( TARGET gdas_soca_diagnostics.x
                        SOURCES diagnostics/gdas_soca_diagnostics.cc)
target_compile_features( gdas_soca_diagnostics.x PUBLIC cxx_std_11)
target_include_directories(gdas_soca_diagnostics.x PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/diagnostics)
target_link_libraries( gdas_soca_diagnostics.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca gdas_soca_diagnostics)
target_link_libraries( gdas_soca_diagnostics.x PRIVATE stdc++fs)

# Increment post processing
ecbuild_add_executable( TARGET gdas_soca_incr_handler.x
                        SOURCES gdas_soca_incr_handler.cc ../genutils/Flood.cc gdas_postprocincr.h gdas_postprocincr.cc)
target_compile_features( gdas_soca_incr_handler.x PUBLIC cxx_std_11)
target_link_libraries( gdas_soca_incr_handler.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca)
target_link_libraries( gdas_soca_incr_handler.x PRIVATE stdc++fs)

# Ensemble members post processing
ecbuild_add_executable( TARGET gdas_soca_ens_handler.x
                        SOURCES gdas_soca_ens_handler.cc ../genutils/Flood.cc gdas_postprocincr.h gdas_postprocincr.cc)
target_compile_features( gdas_soca_ens_handler.x PUBLIC cxx_std_11)
target_link_libraries( gdas_soca_ens_handler.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca)
target_link_libraries( gdas_soca_ens_handler.x PRIVATE stdc++fs)

# Hybrid-Weight
ecbuild_add_executable( TARGET gdas_soca_hybridweights.x
                        SOURCES gdas_soca_hybridweights.cc )
target_compile_features( gdas_soca_hybridweights.x PUBLIC cxx_std_17)
target_link_libraries( gdas_soca_hybridweights.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca)

# Obs Stats
ecbuild_add_executable( TARGET gdas_soca_obsstats.x
                        SOURCES gdas_soca_obsstats.cc )
target_compile_features( gdas_soca_obsstats.x PUBLIC cxx_std_17)
target_link_libraries( gdas_soca_obsstats.x PUBLIC NetCDF::NetCDF_CXX oops ioda)

# Diag B
add_subdirectory( diagb )

# Coupled stuff
add_subdirectory( coupled )

# Testing
add_subdirectory( test )
