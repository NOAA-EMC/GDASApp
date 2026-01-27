# Diag B
ecbuild_add_executable( TARGET gcdas_fv3jedi_chem_diagb.x
                        SOURCES gdas_fv3jedi_chem_diagb.cc )
target_compile_features( gcdas_fv3jedi_chem_diagb.x PUBLIC cxx_std_17)
target_link_libraries( gcdas_fv3jedi_chem_diagb.x PUBLIC NetCDF::NetCDF_CXX oops atlas fv3jedi)

add_subdirectory(viirsaod)
