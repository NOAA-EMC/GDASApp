# Increment post processing
ecbuild_add_executable( TARGET fv3jedi_fv3inc.x
                        SOURCES fv3jedi_fv3inc.cc fv3jedi_fv3inc.h)
target_compile_features( fv3jedi_fv3inc.x PUBLIC cxx_std_17)
target_link_libraries( fv3jedi_fv3inc.x PUBLIC NetCDF::NetCDF_CXX oops fv3jedi)

# Ensemble increment recentering
ecbuild_add_executable( TARGET fv3jedi_correction_increment.x
                        SOURCES fv3jedi_correction_increment.cc fv3jedi_correction_increment.h)
target_compile_features( fv3jedi_correction_increment.x PUBLIC cxx_std_17)
target_link_libraries( fv3jedi_correction_increment.x PUBLIC NetCDF::NetCDF_CXX oops fv3jedi)

# Increment addition
ecbuild_add_executable( TARGET fv3jedi_add_increments.x
                        SOURCES fv3jedi_add_increments.cc fv3jedi_add_increments.h)
target_compile_features( fv3jedi_add_increments.x PUBLIC cxx_std_17)
target_link_libraries( fv3jedi_add_increments.x PUBLIC NetCDF::NetCDF_CXX oops fv3jedi)
