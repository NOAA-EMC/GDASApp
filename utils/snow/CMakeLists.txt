# Ensemble recenter of snow
ecbuild_add_executable( TARGET gdasapp_snow_ensrecenter.x
                        SOURCES snow_ensrecenter.cc )
target_compile_features( gdasapp_snow_ensrecenter.x PUBLIC cxx_std_17)
target_link_libraries( gdasapp_snow_ensrecenter.x PUBLIC NetCDF::NetCDF_CXX oops atlas fv3jedi)
