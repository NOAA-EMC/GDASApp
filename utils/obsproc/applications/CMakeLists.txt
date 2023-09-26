list( APPEND gdasapp_rads2ioda_src_files
  gdas_obsprovider2ioda.cc
  gdas_obsprovider2ioda.h
  )
ecbuild_add_executable( TARGET gdas_obsprovider2ioda.x
                        SOURCES ${gdasapp_rads2ioda_src_files} )

target_compile_features( gdas_obsprovider2ioda.x PUBLIC cxx_std_17)
target_link_libraries( gdas_obsprovider2ioda.x PUBLIC oops ioda NetCDF::NetCDF_CXX)
