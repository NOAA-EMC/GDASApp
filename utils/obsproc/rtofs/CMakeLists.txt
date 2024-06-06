# message("RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR")
# message("Current source directory: ${CMAKE_CURRENT_SOURCE_DIR}")
# message("Current binary directory: ${CMAKE_CURRENT_BINARY_DIR}")
# message("CMAKE_INCLUDE_PATH=${CMAKE_INCLUDE_PATH}")
# message("C_INCLUDE_PATH=${C_INCLUDE_PATH}")
# message("CPLUS_INCLUDE_PATH=${CPLUS_INCLUDE_PATH}")
# message("RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR")

# include_directories(${CMAKE_SOURCE_DIR})

set(
	rtofs_src_files
	RTOFSDataFile.h
	RTOFSDataFile.cc
	RTOFSOb.h
	RTOFSOb.cc
	util.cc
	util.h
)

list(
	APPEND gdasapp_provider2ioda_src_files
	${rtofs_src_files}
)


add_library(rtofs STATIC
	${rtofs_src_files}
)
#  ecbuild_add_library(
	# TARGET rtofs
	# TYPE STATIC
	# SOURCES ${rtofs_src_files}
# )

target_compile_features(
	rtofs
	PUBLIC cxx_std_17
)

target_link_libraries( rtofs PUBLIC oops ioda NetCDF::NetCDF_CXX )

# target_link_libraries(rtofs PUBLIC oops)
target_include_directories( rtofs PUBLIC ${oops_INCLUDE_DIRS} )
