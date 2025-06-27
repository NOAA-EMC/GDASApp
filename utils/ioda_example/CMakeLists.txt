ecbuild_add_executable( TARGET gdas_ioda_mean.x
                        SOURCES gdas_ioda_mean.cc )

target_compile_features( gdas_ioda_mean.x PUBLIC cxx_std_17)
target_link_libraries( gdas_ioda_mean.x PUBLIC oops ioda)

