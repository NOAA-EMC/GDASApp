project(gdas-utils LANGUAGES C CXX )

find_package(NetCDF REQUIRED COMPONENTS CXX)
find_package(oops REQUIRED)
find_package(atlas REQUIRED)
find_package(soca REQUIRED)

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
