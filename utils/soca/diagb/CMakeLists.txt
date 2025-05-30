ecbuild_add_executable( TARGET gdas_soca_diagb.x
                        SOURCES gdas_soca_diagb.cc )
target_compile_features( gdas_soca_diagb.x PUBLIC cxx_std_17)
target_link_libraries( gdas_soca_diagb.x PUBLIC NetCDF::NetCDF_CXX oops atlas soca)
