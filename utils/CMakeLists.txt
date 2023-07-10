project(gdas-utils LANGUAGES C CXX )

find_package(NetCDF REQUIRED COMPONENTS CXX)
find_package(oops REQUIRED)
find_package(atlas REQUIRED)
find_package(soca REQUIRED)

ecbuild_add_executable( TARGET gdas_socaincr2mom6.x
                        SOURCES gdas_socaincr2mom6.cc )

target_compile_features( gdas_socaincr2mom6.x PUBLIC cxx_std_17)
target_link_libraries( gdas_socaincr2mom6.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca)

ecbuild_add_executable( TARGET gdas_socahybridweights.x
                        SOURCES gdas_socahybridweights.cc )

target_compile_features( gdas_socahybridweights.x PUBLIC cxx_std_17)
target_link_libraries( gdas_socahybridweights.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca)
