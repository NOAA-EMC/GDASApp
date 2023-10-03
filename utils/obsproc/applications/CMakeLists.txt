list( APPEND gdasapp_provider2ioda_src_files
  gdas_obsprovider2ioda.cc
  gdas_obsprovider2ioda.h
  )
ecbuild_add_executable( TARGET gdas_obsprovider2ioda.x
                        SOURCES ${gdasapp_provider2ioda_src_files} )

target_compile_features( gdas_obsprovider2ioda.x PUBLIC cxx_std_17)
target_link_libraries( gdas_obsprovider2ioda.x PUBLIC oops ioda NetCDF::NetCDF_CXX)

ecbuild_add_executable( TARGET gdas_testrun.x
                        SOURCES gdas_testrun.cc )
target_compile_features( gdas_testrun.x PUBLIC cxx_std_17)
target_link_libraries( gdas_testrun.x PUBLIC oops ioda NetCDF::NetCDF_CXX)
