# FV3 dycore
set(OPENMP                ON )
set(32BIT                 OFF)
set(DEBUG                 OFF)
set(MOVING_NEST           OFF)
set(MULTI_GASES           OFF)
set(USE_GFSL63            ON )
set(NO_PHYS               ON )
set(GFS_PHYS              OFF)
set(GFS_TYPES             OFF)
set(use_WRTCOMP           OFF)
set(INTERNAL_FILE_NML     ON )
set(ENABLE_QUAD_PRECISION ON )

add_library(fv3dycore IMPORTED SHARED)
set_target_properties(fv3dycore PROPERTIES IMPORTED_LOCATION ${CMAKE_CURRENT_BINARY_DIR}/fv3/libfv3.${CMAKE_SHARED_LIBRARY_SUFFIX})

message(WARN "WE ARE USING fv3-interface.cmake")
