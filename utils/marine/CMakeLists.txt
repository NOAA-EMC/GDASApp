# Marine utilities written against the generic oops interfaces, built once per model interface

add_library(gdas_marine_utils STATIC gdas_marine_read_nc_interp.cc gdas_marine_ice_physics.cc
                                     gdas_marine_postprocess_ice.cc)
target_include_directories(gdas_marine_utils PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(gdas_marine_utils PUBLIC NetCDF::NetCDF_C atlas oops)

# Marine static-B parameters
if (BUILD_SOCA)
  ecbuild_add_executable( TARGET  gdas_soca_marine_bparams.x
                          SOURCES gdas_soca_marine_bparams.cc )
  target_link_libraries( gdas_soca_marine_bparams.x PUBLIC gdas_marine_utils soca )
endif()

if (BUILD_IJEDI)
  ecbuild_add_executable( TARGET  gdas_ijedi_marine_bparams.x
                          SOURCES gdas_ijedi_marine_bparams.cc )
  target_link_libraries( gdas_ijedi_marine_bparams.x PUBLIC gdas_marine_utils ijedi )
endif()

# Marine increment post processing (JEDI increment -> MOM6 IAU increment, sea-ice restart)
if (BUILD_SOCA)
  ecbuild_add_executable( TARGET  gdas_soca_incr_handler.x
                          SOURCES gdas_soca_incr_handler.cc ../genutils/Flood.cc )
  target_link_libraries( gdas_soca_incr_handler.x PUBLIC gdas_marine_utils soca )
  target_link_libraries( gdas_soca_incr_handler.x PRIVATE stdc++fs )
endif()

if (BUILD_IJEDI)
  ecbuild_add_executable( TARGET  gdas_ijedi_marine_incr_handler.x
                          SOURCES gdas_ijedi_marine_incr_handler.cc ../genutils/Flood.cc )
  target_link_libraries( gdas_ijedi_marine_incr_handler.x PUBLIC gdas_marine_utils ijedi )
  target_link_libraries( gdas_ijedi_marine_incr_handler.x PRIVATE stdc++fs )
endif()
