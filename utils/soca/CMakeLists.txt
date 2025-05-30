# Increment post processing
ecbuild_add_executable( TARGET gdas_soca_incr_handler.x
                        SOURCES gdas_soca_incr_handler.cc gdas_postprocincr.h)
target_compile_features( gdas_soca_incr_handler.x PUBLIC cxx_std_11)
target_link_libraries( gdas_soca_incr_handler.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca)
target_link_libraries( gdas_soca_incr_handler.x PRIVATE stdc++fs)

# Ensemble members post processing
ecbuild_add_executable( TARGET gdas_soca_ens_handler.x
                        SOURCES gdas_soca_ens_handler.cc gdas_postprocincr.h)
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
