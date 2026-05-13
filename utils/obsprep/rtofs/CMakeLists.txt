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
	APPEND obsforge_provider2ioda_src_files
	${rtofs_src_files}
)


add_library(rtofs STATIC
	${rtofs_src_files}
)

target_compile_features(
	rtofs
	PUBLIC cxx_std_17
)

target_link_libraries(rtofs PUBLIC oops ioda NetCDF::NetCDF_CXX)
