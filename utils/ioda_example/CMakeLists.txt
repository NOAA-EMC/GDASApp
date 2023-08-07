ecbuild_add_executable( TARGET gdas_meanioda.x
                        SOURCES gdas_meanioda.cc )

target_compile_features( gdas_meanioda.x PUBLIC cxx_std_17)
target_link_libraries( gdas_meanioda.x PUBLIC oops ioda)

