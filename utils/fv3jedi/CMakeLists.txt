# Increment post processing
ecbuild_add_executable( TARGET gdas_fv3jedi_fv3inc.x
                        SOURCES gdas_fv3jedi_fv3inc.cc fv3jedi_fv3inc.h)
target_compile_features( gdas_fv3jedi_fv3inc.x PUBLIC cxx_std_17)
target_link_libraries( gdas_fv3jedi_fv3inc.x PUBLIC NetCDF::NetCDF_CXX oops fv3jedi)

# Correction increment calculation (for ensemble recentering)
ecbuild_add_executable( TARGET gdas_fv3jedi_correction_increment.x
                        SOURCES gdas_fv3jedi_correction_increment.cc fv3jedi_correction_increment.h)
target_compile_features( gdas_fv3jedi_correction_increment.x PUBLIC cxx_std_17)
target_link_libraries( gdas_fv3jedi_correction_increment.x PUBLIC NetCDF::NetCDF_CXX oops fv3jedi)
