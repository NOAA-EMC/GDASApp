# Copy the bkg files
# ------------------
set(TESTDATA ${PROJECT_BINARY_DIR}/test/testdata )


# Symlink test input yaml files
# -----------------------------
# create testinput dir
set (TESTINPUT_DIR ${PROJECT_BINARY_DIR}/test/soca/testinput)

file(MAKE_DIRECTORY ${TESTINPUT_DIR})

# symlink
foreach(FILENAME ${test_input})
	get_filename_component(filename ${FILENAME} NAME)
	execute_process( COMMAND ${CMAKE_COMMAND} -E create_symlink
		${FILENAME}
		${TESTINPUT_DIR}
	)
endforeach(FILENAME)

# install
install(FILES ${test_input}
        DESTINATION "test/testinput/")

# Test exgdas scripts from the global-worflow
if (WORKFLOW_TESTS)
  add_subdirectory(gw)
endif()

# test for ush/socaincr2mom6.py
add_test(NAME test_gdasapp_soca_nsst_increment_to_mom6
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/socaincr2mom6.sh ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca)
set_tests_properties(
        test_gdasapp_soca_nsst_increment_to_mom6
PROPERTIES
ENVIRONMENT "data=${TESTDATA};PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH}")


###########################################################################
# bufr to ioda tests:
###########################################################################

# prepare a test.yaml file from test.yaml.in by replacing
# placeholder patterns __BUFRINPUTDIR__ and __IODAOUTPUTDIR__
# with actual directory paths
function(CREATE_CONFIG_FILE test_config_in test_config_out bufr_input_dir ioda_output_dir)
	file(READ "${test_config_in}" file_content)
	string(REPLACE "__BUFRINPUTDIR__" "\"${bufr_input_dir}\"" temp_content "${file_content}")
	string(REPLACE "__IODAOUTPUTDIR__" "\"${ioda_output_dir}\"" temp_content2 "${temp_content}")
	file(WRITE "${test_config_out}" "${temp_content2}")
endfunction()


set(TEST_WORKING_DIR ${PROJECT_BINARY_DIR}/test/soca)
message("bufr to ioda: TEST_WORKING_DIR = ${TEST_WORKING_DIR}")

set(MARINE_BUFR2IODA_DIR ${PROJECT_SOURCE_DIR}/ush/ioda/bufr2ioda/marine)
set(MARINE_BUFR2IODA_DIR ${MARINE_BUFR2IODA_DIR}/b2i)
set(CONFIG_DIR ${PROJECT_SOURCE_DIR}/test/soca/testinput)
set(TESTREF_DIR ${PROJECT_SOURCE_DIR}/test/soca/testref)

# find the staging directory for bufr test input files ${BUFR_TEST_DIR}
# checking on orion and hera
# bufr input files on orion:
set(BUFR_TEST_DIR
	"/work/noaa/da/marineda/gfs-marine/data/obs/ci/bufr"
)
if (NOT EXISTS ${BUFR_TEST_DIR})
	# bufr input files on hera:
	set(BUFR_TEST_DIR
		"/scratch1/NCEPDEV/da/common/ci/bufr"
	)
endif()
if (NOT EXISTS ${BUFR_TEST_DIR})
	message("staging directory for BUFR test files ${BUFR_TEST_DIR} not found")
	set(GENERATE_BUFR2IODA_TESTS FALSE)
else()
	set(GENERATE_BUFR2IODA_TESTS TRUE)
endif()



function(ADD_INSITU_TEST testname testbufr)
	# set(CONFIG_TYPE "json")
	set(CONFIG_TYPE "yaml")
	set(DATE "2021063006")
	set(TEST "bufr2ioda_insitu_${testname}")

	set(TESTREF_FILE "${TEST}_${DATE}.ref")

	# stage the input file to directory ${BUFR_INPUT_DIR}
	set(BUFR_INPUT_DIR ${TEST_WORKING_DIR})
	set(BUFR_TEST_FILE "${DATE}-gdas.t06z.${testbufr}.tm00.bufr_d")
	set(BUFR_FILE "${BUFR_TEST_DIR}/${BUFR_TEST_FILE}")
	if (NOT EXISTS ${BUFR_FILE})
		message(FATAL_ERROR "BUFR file ${BUFR_FILE} not found")
	endif()
	file(COPY ${BUFR_FILE} DESTINATION ${BUFR_INPUT_DIR})

	# stage the config file
	set(CONFIG_FILE_NAME ${TEST}_${DATE}.${CONFIG_TYPE})
	set(CONFIG_FILE_IN "${CONFIG_DIR}/${CONFIG_FILE_NAME}.in")
	set(CONFIG_FILE "${TEST_WORKING_DIR}/${CONFIG_FILE_NAME}")
	set(IODA_OUTPUT_DIR ${TEST_WORKING_DIR})
	CREATE_CONFIG_FILE(
		${CONFIG_FILE_IN}
		${CONFIG_FILE}
		${BUFR_INPUT_DIR}
		${IODA_OUTPUT_DIR}
	)

	add_test(
		NAME test_${TEST}
		COMMAND ${MARINE_BUFR2IODA_DIR}/${TEST}.py -c ${CONFIG_FILE} -t ${TESTREF_DIR}/${TESTREF_FILE}
		WORKING_DIRECTORY ${TEST_WORKING_DIR}
	)
endfunction()


if (GENERATE_BUFR2IODA_TESTS)
	ADD_INSITU_TEST("profile_argo" "subpfl")
	ADD_INSITU_TEST("profile_bathy" "bathy")
	ADD_INSITU_TEST("profile_glider" "subpfl")
	ADD_INSITU_TEST("profile_tesac" "tesac")
	ADD_INSITU_TEST("profile_xbtctd" "xbtctd")
	ADD_INSITU_TEST("surface_trkob" "trkob")
endif()
