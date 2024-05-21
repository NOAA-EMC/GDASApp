# Ensemble recenter of land
ecbuild_add_executable( TARGET gdasapp_land_ensrecenter.x
                        SOURCES land_ensrecenter.cc )
target_compile_features( gdasapp_land_ensrecenter.x PUBLIC cxx_std_17)
target_link_libraries( gdasapp_land_ensrecenter.x PUBLIC NetCDF::NetCDF_CXX oops atlas fv3jedi)
