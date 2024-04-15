# Diag B
ecbuild_add_executable( TARGET chem_diagb.x
                        SOURCES chem_diagb.cc )
target_compile_features( chem_diagb.x PUBLIC cxx_std_17)
target_link_libraries( gdasapp_chem_diagb.x PUBLIC NetCDF::NetCDF_CXX oops atlas fv3jedi)
