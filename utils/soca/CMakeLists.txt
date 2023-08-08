# Increment post processing
ecbuild_add_executable( TARGET gdas_incr_handler.x
                        SOURCES gdas_incr_handler.cc gdas_postprocincr.h)
target_compile_features( gdas_incr_handler.x PUBLIC cxx_std_17)
target_link_libraries( gdas_incr_handler.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca)

# Hybrid-Weight
ecbuild_add_executable( TARGET gdas_socahybridweights.x
                        SOURCES gdas_socahybridweights.cc )
target_compile_features( gdas_socahybridweights.x PUBLIC cxx_std_17)
target_link_libraries( gdas_socahybridweights.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca)
