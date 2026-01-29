# Diag B
ecbuild_add_executable( TARGET gdas_fv3jedi_chem_diagb.x
                        SOURCES gdas_fv3jedi_chem_diagb.cc )
target_compile_features( gdas_fv3jedi_chem_diagb.x PUBLIC cxx_std_17)
target_link_libraries( gdas_fv3jedi_chem_diagb.x PUBLIC NetCDF::NetCDF_CXX oops atlas fv3jedi)
add_subdirectory(viirsaod)
