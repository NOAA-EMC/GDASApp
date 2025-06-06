# Ensemble recenter of land
ecbuild_add_executable( TARGET gdasapp_land_ensrecenter.x
                        SOURCES land_ensrecenter.cc )
target_compile_features( gdasapp_land_ensrecenter.x PUBLIC cxx_std_17)
target_link_libraries( gdasapp_land_ensrecenter.x PUBLIC NetCDF::NetCDF_CXX oops atlas fv3jedi)

# Snow cover fraction to IODA on the model grid
ecbuild_add_executable( TARGET gdas_scf_to_ioda.x
                        SOURCES gdas_scf_to_ioda.cc gdas_calc_scf_to_ioda.cc )
target_compile_features( gdas_scf_to_ioda.x PUBLIC cxx_std_17)
target_link_libraries( gdas_scf_to_ioda.x PUBLIC NetCDF::NetCDF_CXX oops atlas ioda fv3jedi)
