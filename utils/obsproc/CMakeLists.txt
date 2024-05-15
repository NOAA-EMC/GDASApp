
add_subdirectory(rtofs)

# add_library(obsproc STATIC
	# Ghrsst2Ioda.h
	# IcecAmsr2Ioda.h
	# NetCDFToIodaConverter.h
	# Rads2Ioda.h
	# RTOFSInSitu.h
	# Smap2Ioda.h
	# Smos2Ioda.h
	# superob.h
	# util.h
	# Viirsaod2Ioda.h
# )
# target_compile_features(
	# onsproc
	# PUBLIC cxx_std_17
# )
# target_link_libraries(
	# obsproc
	# PUBLIC oops ioda NetCDF::NetCDF_CXX
# )

add_subdirectory(applications)
