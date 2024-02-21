# Increment post processing
ecbuild_add_executable( TARGET gdas_jediinc2fv3.x
                        SOURCES gdas_jediinc2fv3.cc gdas_jediinc2fv3.h)
target_compile_features( gdas_jediinc2fv3.x PUBLIC cxx_std_17)
target_link_libraries( gdas_jediinc2fv3.x PUBLIC NetCDF::NetCDF_CXX oops fv3jedi)
