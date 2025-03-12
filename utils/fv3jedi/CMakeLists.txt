# Increment post processing
ecbuild_add_executable( TARGET fv3jedi_fv3inc.x
                        SOURCES fv3jedi_fv3inc.cc fv3jedi_fv3inc.h)
target_compile_features( fv3jedi_fv3inc.x PUBLIC cxx_std_17)
target_link_libraries( fv3jedi_fv3inc.x PUBLIC NetCDF::NetCDF_CXX oops fv3jedi)

# Correction increment calculation (for ensemble recentering)
ecbuild_add_executable( TARGET fv3jedi_correction_increment.x
                        SOURCES fv3jedi_correction_increment.cc fv3jedi_correction_increment.h)
target_compile_features( fv3jedi_correction_increment.x PUBLIC cxx_std_17)
target_link_libraries( fv3jedi_correction_increment.x PUBLIC NetCDF::NetCDF_CXX oops fv3jedi)

# Ensemble AddIncrement
ecbuild_add_executable( TARGET fv3jedi_ensemble_add_increment.x
                        SOURCES fv3jedi_ensemble_add_increment.cc)
target_compile_features( fv3jedi_ensemble_add_increment.x PUBLIC cxx_std_17)
target_link_libraries( fv3jedi_ensemble_add_increment.x PUBLIC NetCDF::NetCDF_CXX oops fv3jedi)
