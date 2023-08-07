ecbuild_add_executable( TARGET gdas_dumpioda.x
                        SOURCES gdas_dumpioda.cc )

target_compile_features( gdas_dumpioda.x PUBLIC cxx_std_17)
target_link_libraries( gdas_dumpioda.x PUBLIC oops ioda)

