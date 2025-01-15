# Copy the bkg files
# ------------------
set(TESTDATA ${PROJECT_BINARY_DIR}/test/testdata )


# Symlink test input yaml files
# -----------------------------
# create testinput dir
set (TESTINPUT_DIR ${PROJECT_BINARY_DIR}/test/marine/testinput)

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


###########################################################################
# bufr to ioda tests:
###########################################################################

find_package(Python REQUIRED)
# Extract the major and minor version (e.g., "3.10" from "3.10.13")
string(REGEX REPLACE "^([0-9]+\\.[0-9]+).*" "\\1" PYTHON_MAJOR_MINOR ${Python_VERSION})
set(PYIODACONV_DIR "${PROJECT_SOURCE_DIR}/build/lib/python${PYTHON_MAJOR_MINOR}/")

set(TEST_WORKING_DIR ${PROJECT_BINARY_DIR}/test/marine)
set(MARINE_BUFR2IODA_DIR ${PROJECT_SOURCE_DIR}/ush/ioda/bufr2ioda/marine)
# set(MARINE_BUFR2IODA_DIR ${MARINE_BUFR2IODA_DIR}/newb2i)
set(MARINE_BUFR2IODA_DIR ${MARINE_BUFR2IODA_DIR}/b2iron)
set(CONFIG_DIR ${PROJECT_SOURCE_DIR}/test/marine/testinput)
set(TESTREF_DIR ${PROJECT_SOURCE_DIR}/test/marine/testref)


# prepare a test.yaml file from test.yaml.in by replacing
# placeholder patterns 
# __BUFRINPUTDIR__ 
# __IODAOUTPUTDIR__ 
# __OCEANBASIN__
# __CONFIGDIR__
# with actual directory paths
function(CREATE_CONFIG_FILE 
	test_config_in 
	test_config_out 
	bufr_input_dir 
	ioda_output_dir
	ocean_basin_file
)
	file(READ "${test_config_in}" file_content)
	string(REPLACE "__BUFRINPUTDIR__" "\"${bufr_input_dir}\"" temp_content "${file_content}")
	string(REPLACE "__IODAOUTPUTDIR__" "\"${ioda_output_dir}\"" temp_content2 "${temp_content}")
	string(REPLACE "__OCEANBASIN__" "\"${ocean_basin_file}\"" temp_content3 "${temp_content2}")
	string(REPLACE "__CONFIGDIR__" ${CONFIG_DIR} temp_content4 "${temp_content3}")
	file(WRITE "${test_config_out}" "${temp_content4}")
endfunction()


function(CHECK_AND_SET_PATH PATH1 PATH2 RESULT_VAR)
    # Check if PATH1 exists
    if(EXISTS ${PATH1})
        set(${RESULT_VAR} ${PATH1} PARENT_SCOPE)
        set(${RESULT_VAR}_EXISTS TRUE PARENT_SCOPE)
        return()
    endif()

    # Check if PATH2 exists
    if(EXISTS ${PATH2})
        set(${RESULT_VAR} ${PATH2} PARENT_SCOPE)
        set(${RESULT_VAR}_EXISTS TRUE PARENT_SCOPE)
        return()
    endif()

    # If neither path exists
    set(${RESULT_VAR} "" PARENT_SCOPE)
    set(${RESULT_VAR}_EXISTS FALSE PARENT_SCOPE)
endfunction()


# find the input files
set(BUFR_TEST_DIR_ORION
	"/work/noaa/da/marineda/gfs-marine/data/obs/ci/bufr"
)
set(BUFR_TEST_DIR_HERA
	"/scratch1/NCEPDEV/da/common/ci/bufr"
)
CHECK_AND_SET_PATH(
	${BUFR_TEST_DIR_ORION} 
	${BUFR_TEST_DIR_HERA} 
	BUFR_TEST_DIR
)
if (NOT BUFR_TEST_DIR_EXISTS)
	message(WARNING "BUFR test file directory not found -- bufr to ioda tests not generated.")
	set(GENERATE_BUFR2IODA_TESTS FALSE)
else()
    # message(STATUS "Found bufr test directory: ${BUFR_TEST_DIR}")

	set(OCEAN_BASIN_FILE_HERA
		"/scratch2/NCEPDEV/ocean/Guillaume.Vernieres/data/static/common/RECCAP2_region_masks_all_v20221025.nc"
	)
	set(OCEAN_BASIN_FILE_ORION
		"/work/noaa/global/glopara/fix/gdas/soca/20240802/common/RECCAP2_region_masks_all_v20221025.nc"
	)
	CHECK_AND_SET_PATH(
		${OCEAN_BASIN_FILE_ORION} 
		${OCEAN_BASIN_FILE_HERA} 
		OCEAN_BASIN_FILE
	)
	if (NOT OCEAN_BASIN_FILE_EXISTS)
		message(WARNING "Ocean basin data file not found -- bufr to ioda tests not generated.")
		set(GENERATE_BUFR2IODA_TESTS FALSE)
	endif()
	# message(STATUS "Found ocean basin data in ${OCEAN_BASIN_FILE}")
	set(GENERATE_BUFR2IODA_TESTS TRUE)
endif()


function(ADD_INSITU_TEST testname testbufr)
	# set(CONFIG_TYPE "json")
	set(CONFIG_TYPE "yaml")

	set(DATE "2019010700")
	set(CYCLE "00")
	# if (testbufr STREQUAL "dbuoy")
		# set(DATE "2019010700")
		# set(CYCLE "00")
	# else()
		# set(DATE "2021063006")
		# set(CYCLE "06")
	# endif()

	set(TESTEXEC "bufr2ioda_insitu_${testname}.py")
	set(TEST "bufr2ioda_insitu_${testname}_${testbufr}")

	set(TESTREF_FILE "${TEST}_${DATE}.ref")

	# stage the input file to directory ${BUFR_INPUT_DIR}
	set(BUFR_INPUT_DIR ${TEST_WORKING_DIR})
	set(BUFR_TEST_FILE "${DATE}-gdas.t${CYCLE}z.${testbufr}.tm00.bufr_d")
	set(BUFR_FILE "${BUFR_TEST_DIR}/${BUFR_TEST_FILE}")
	if (NOT EXISTS ${BUFR_FILE})
		message(WARNING "BUFR file ${BUFR_FILE} not found, test not generated")
		return()
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
		${OCEAN_BASIN_FILE}
	)

	add_test(
		NAME test_gdasapp_${TEST}
		COMMAND ${MARINE_BUFR2IODA_DIR}/${TESTEXEC} -c ${CONFIG_FILE} -t ${TESTREF_DIR}/${TESTREF_FILE}
		WORKING_DIRECTORY ${TEST_WORKING_DIR}
	)
	set_property(
		TEST test_gdasapp_${TEST}
		APPEND PROPERTY 
			ENVIRONMENT "PYTHONPATH=${PYIODACONV_DIR}:$ENV{PYTHONPATH}"
	)
endfunction()



if (GENERATE_BUFR2IODA_TESTS)
	ADD_INSITU_TEST("profile_argo" "subpfl")
	ADD_INSITU_TEST("profile_bathy" "bathy")
	ADD_INSITU_TEST("profile_glider" "subpfl")
	ADD_INSITU_TEST("profile_tesac" "tesac")
	ADD_INSITU_TEST("profile_tropical" "dbuoy")
	ADD_INSITU_TEST("profile_tropical" "mbuoyb")
	ADD_INSITU_TEST("profile_xbtctd" "xbtctd")
    ADD_INSITU_TEST("surface_altkob" "altkob")
    ADD_INSITU_TEST("surface_cstgd" "cstgd")
	ADD_INSITU_TEST("surface_drifter" "dbuoy")
	ADD_INSITU_TEST("surface_drifter" "dbuoyb")
	ADD_INSITU_TEST("surface_lcman" "lcman")
    ADD_INSITU_TEST("surface_shipsu" "shipsu")
	ADD_INSITU_TEST("surface_trkob" "trkob")
endif()
