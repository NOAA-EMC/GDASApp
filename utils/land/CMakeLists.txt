# Ensemble recenter of land
ecbuild_add_executable( TARGET gdas_fv3jedi_land_ensrecenter.x
                        SOURCES gdas_fv3jedi_land_ensrecenter.cc )
target_compile_features( gdas_fv3jedi_land_ensrecenter.x PUBLIC cxx_std_17)
target_link_libraries( gdas_fv3jedi_land_ensrecenter.x PUBLIC NetCDF::NetCDF_CXX oops atlas fv3jedi)