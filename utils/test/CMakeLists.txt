#eT Create Data directory for test input config and symlink all files
list( APPEND utils_test_input
  testinput/gdas_meanioda.yaml
  testinput/gdas_rads2ioda.yaml
  testinput/gdas_ghrsst2ioda.yaml
  testinput/gdas_rtofstmp.yaml
  testinput/gdas_rtofssal.yaml
  testinput/gdas_smap2ioda.yaml
  testinput/gdas_smos2ioda.yaml
  testinput/gdas_icecabi2ioda.yaml
  testinput/gdas_icecamsr2ioda.yaml
  testinput/gdas_icecmirs2ioda.yaml
  testinput/gdas_icecjpssrr2ioda.yaml
  testinput/gdas_insituall2ioda.yaml
  testinput/gdas_viirsaod2ioda.yaml
)

set( gdas_utils_test_ref
  testref/rads2ioda.test
  testref/ghrsst2ioda.test
  testref/rtofstmp.test
  testref/rtofssal.test
  testref/smap2ioda.test
  testref/smos2ioda.test
  testref/icecabi2ioda.test
  testref/icecamsr2ioda.test
  testref/icecmirs2ioda.test
  testref/icecjpssrr2ioda.test
  testref/insituall2ioda.test
  testref/viirsaod2ioda.test
)

file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/testinput)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/testrun)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc/testref)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc/testoutput)

CREATE_SYMLINK( ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR}/obsproc ${gdas_utils_test_ref} )
CREATE_SYMLINK( ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR} ${utils_test_input} )

# copy the cpp linter script
execute_process( COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_CURRENT_SOURCE_DIR}/cpplint.py ${CMAKE_BINARY_DIR}/bin/${PROJECT_NAME}_cpplint.py)

# add linter for the utils
# TODO: the linter complains about local .h files included in the .cc
# in the rtofs directory
# the exclude argument needs to be removed
ecbuild_add_test( TARGET test_gdasapp_util_coding_norms
                  TYPE SCRIPT
                  COMMAND ${CMAKE_BINARY_DIR}/bin/${PROJECT_NAME}_cpplint.py
                  ARGS --quiet --recursive --exclude=${CMAKE_CURRENT_SOURCE_DIR}/../obsproc/rtofs/*.cc ${CMAKE_CURRENT_SOURCE_DIR}/../ 
                  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/bin )

# Test example IODA utility that computes the mean of a variable
ecbuild_add_test( TARGET  test_gdasapp_util_ioda_example
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_meanioda.x
                  ARGS    "testinput/gdas_meanioda.yaml"
                  LIBS    gdas-utils)

# Prepare data for the IODA converters
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)
ecbuild_add_test( TARGET  test_gdasapp_util_prepdata
                  COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/prepdata.sh
                  ARGS    ${CMAKE_CURRENT_SOURCE_DIR}
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)

# Test the RADS to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_rads2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_rads2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc
                  TEST_DEPENDS test_gdasapp_util_prepdata)

# Test the GHRSST to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_ghrsst2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_ghrsst2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc
                  TEST_DEPENDS test_gdasapp_util_prepdata)

# copy rtofs binary input files to the testing area
# and generate the tests

set(RTOFS_INPUT_FILE1 "rtofsinsitu_2024032600.profile")
set(RTOFS_INPUT_FILE2 "rtofsinsitu_2024032700.profile")

# rtofs directory on orion:
set(RTOFS_FILES_PATH
	"/work/noaa/da/marineda/gfs-marine/data/obs/ci/obs"
)
if (NOT EXISTS ${RTOFS_FILES_PATH})
	# rtofs directory on hera:
	set(RTOFS_FILES_PATH
		"/scratch1/NCEPDEV/da/common/ci/obs"
	)
endif()
if (NOT EXISTS ${RTOFS_FILES_PATH})
	message("Error: staging directory for RTOFS test files not found")
else()
	set(RTOFS_FILE1 "${RTOFS_FILES_PATH}/${RTOFS_INPUT_FILE1}")
	set(RTOFS_FILE2 "${RTOFS_FILES_PATH}/${RTOFS_INPUT_FILE2}")
	set(DESTINATION_DIR "${CMAKE_CURRENT_BINARY_DIR}/obsproc")

	if (EXISTS ${RTOFS_FILE1} AND EXISTS ${RTOFS_FILE2})
		message("Found RTOFS files; generating tests")

		file(COPY ${RTOFS_FILE1} DESTINATION ${DESTINATION_DIR})
		file(COPY ${RTOFS_FILE2} DESTINATION ${DESTINATION_DIR})

		# Test the RTOFStmp to IODA converter
		ecbuild_add_test( TARGET  test_gdasapp_util_rtofstmp
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
				  ARGS    "../testinput/gdas_rtofstmp.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)

		# Test the RTOFSsal to IODA converter
		ecbuild_add_test( TARGET  test_gdasapp_util_rtofssal
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
				  ARGS    "../testinput/gdas_rtofssal.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc)
	else()
		message("Error: RTOFS input files not found; no test generated.")
	endif()
endif()


# Test the SMAP to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_smap2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_smap2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc
                  TEST_DEPENDS test_gdasapp_util_prepdata)

# Test the SMOS to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_smos2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_smos2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc
                  TEST_DEPENDS test_gdasapp_util_prepdata)

# Test the VIIRS AOD to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_viirsaod2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_viirsaod2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc
                  TEST_DEPENDS test_gdasapp_util_prepdata)

# Test the ABI to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_icecabi2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_icecabi2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc
                  TEST_DEPENDS test_gdasapp_util_prepdata)

# Test the AMSR2 to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_icecamsr2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_icecamsr2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc
                  TEST_DEPENDS test_gdasapp_util_prepdata)

# Test the MIRS to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_icecmirs2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_icecmirs2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc
                  TEST_DEPENDS test_gdasapp_util_prepdata)

# Test the JPSSRR to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_icecjpssrr2ioda
                  COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_icecjpssrr2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc
                  TEST_DEPENDS test_gdasapp_util_prepdata)

# Test the INSITU to IODA converter
ecbuild_add_test( TARGET  test_gdasapp_util_insituall2ioda
	          COMMAND ${CMAKE_BINARY_DIR}/bin/gdas_obsprovider2ioda.x
                  ARGS    "../testinput/gdas_insituall2ioda.yaml"
                  LIBS    gdas-utils
                  WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obsproc
                  TEST_DEPENDS test_gdasapp_util_prepdata)
