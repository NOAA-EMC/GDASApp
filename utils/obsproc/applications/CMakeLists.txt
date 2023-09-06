ecbuild_add_executable( TARGET gdas_rads2ioda.x
                        SOURCES gdas_rads2ioda.cc )

target_compile_features( gdas_rads2ioda.x PUBLIC cxx_std_17)
target_link_libraries( gdas_rads2ioda.x PUBLIC oops ioda)
