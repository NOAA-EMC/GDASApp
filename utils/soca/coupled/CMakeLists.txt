ecbuild_add_executable( TARGET gdas_soca_to_fv3.x
                        SOURCES gdas_soca_to_fv3.cc )
target_compile_features( gdas_soca_to_fv3.x PUBLIC cxx_std_17)
target_link_libraries( gdas_soca_to_fv3.x PUBLIC NetCDF::NetCDF_CXX oops fv3jedi soca)
