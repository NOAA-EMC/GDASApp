# Find Python (required for running tests)
find_package(Python REQUIRED)
string(REGEX REPLACE "^([0-9]+\\.[0-9]+).*" "\\1" PYTHON_MAJOR_MINOR ${Python_VERSION})
set(PYIODACONV_DIR "${CMAKE_BINARY_DIR}/lib/python${PYTHON_MAJOR_MINOR}:${CMAKE_BINARY_DIR}/lib/python${PYTHON_MAJOR_MINOR}/site-packages")

# Define test input YAML files
list(APPEND b2i_test_input
    testinput/bufr2ioda_insitu_profile_argo_2021063006.yaml.in
    testinput/bufr2ioda_insitu_profile_bathy_2021063006.yaml.in
    testinput/bufr2ioda_insitu_profile_glider_2021063006.yaml.in
    testinput/bufr2ioda_insitu_profile_tesac_2021063006.yaml.in
    testinput/bufr2ioda_insitu_profile_xbtctd_2021063006.yaml.in
    testinput/bufr2ioda_insitu_surface_trkob_2021063006.yaml.in
	testinput/bufr2ioda_insitu_profile_taotriton_2025061900.yaml.in
	testinput/bufr2ioda_insitu_profile_pirata_2025061900.yaml.in
	testinput/bufr2ioda_insitu_profile_rama_2025061900.yaml.in
	testinput/bufr2ioda_insitu_surface_ndbc_2025061900.yaml.in
	testinput/bufr2ioda_insitu_surface_dbuoyb_drifter_2019010700.yaml.in
)

# Define reference output files
list(APPEND b2i_test_ref
    testref/bufr2ioda_insitu_profile_argo_2021063006.ref
    testref/bufr2ioda_insitu_profile_bathy_2021063006.ref
    testref/bufr2ioda_insitu_profile_glider_2021063006.ref
    testref/bufr2ioda_insitu_profile_tesac_2021063006.ref
    testref/bufr2ioda_insitu_profile_xbtctd_2021063006.ref
    testref/bufr2ioda_insitu_surface_trkob_2021063006.ref
	testref/bufr2ioda_insitu_profile_taotriton_2025061900.ref
	testref/bufr2ioda_insitu_profile_pirata_2025061900.ref
	testref/bufr2ioda_insitu_profile_rama_2025061900.ref
	testref/bufr2ioda_insitu_surface_ndbc_2025061900.ref
	testref/bufr2ioda_insitu_surface_dbuoyb_drifter_2019010700.ref
)

# Set up b2i-specific test directories
set(B2I_TEST_DIR ${CMAKE_CURRENT_BINARY_DIR}/b2i/test)
set(B2I_TESTINPUT_DIR ${B2I_TEST_DIR}/testinput)
set(B2I_TESTREF_DIR ${B2I_TEST_DIR}/testref)
set(B2I_TESTOUTPUT_DIR ${B2I_TEST_DIR}/testoutput)

file(MAKE_DIRECTORY ${B2I_TESTINPUT_DIR})
file(MAKE_DIRECTORY ${B2I_TESTREF_DIR})
file(MAKE_DIRECTORY ${B2I_TESTOUTPUT_DIR})

# Symlink test input and reference files
foreach(FILENAME ${b2i_test_input})
    get_filename_component(filename ${FILENAME} NAME)
    file(CREATE_LINK ${CMAKE_CURRENT_SOURCE_DIR}/${FILENAME}
         ${B2I_TESTINPUT_DIR}/${filename}
         SYMBOLIC)
endforeach()

foreach(FILENAME ${b2i_test_ref})
    get_filename_component(filename ${FILENAME} NAME)
    file(CREATE_LINK ${CMAKE_CURRENT_SOURCE_DIR}/${FILENAME}
         ${B2I_TESTREF_DIR}/${filename}
         SYMBOLIC)
endforeach()

# Define paths for BUFR-to-IODA scripts and executable
# careful: this assume the test dir is a subdir of the script dir
set(B2I_SCRIPT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/..")

# Function to process .in files
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
    file(WRITE "${test_config_out}" "${temp_content3}")
endfunction()

function(CHECK_AND_SET_PATH RESULT_VAR PATH_LIST)
    foreach(PATH IN LISTS PATH_LIST)
        if(EXISTS ${PATH})
            set(${RESULT_VAR} ${PATH} PARENT_SCOPE)
            set(${RESULT_VAR}_EXISTS TRUE PARENT_SCOPE)
            return()
        endif()
    endforeach()

    # If none of the paths exist
    set(${RESULT_VAR} "" PARENT_SCOPE)
    set(${RESULT_VAR}_EXISTS FALSE PARENT_SCOPE)
endfunction()


# Locate BUFR input and ocean basin files
set(BUFR_TEST_DIR_ORION "/work/noaa/da/marineda/gfs-marine/data/obs/ci/bufr")
set(BUFR_TEST_DIR_URSA "/scratch3/NCEPDEV/da/common/ci/bufr")
set(BUFR_TEST_DIR_WCOSS2 "/lfs/h2/emc/da/noscrub/common/ci/bufr")
set(BUFR_TEST_DIR_PATH_LIST
    ${BUFR_TEST_DIR_ORION}
    ${BUFR_TEST_DIR_URSA}
    ${BUFR_TEST_DIR_WCOSS2}
)
CHECK_AND_SET_PATH(
    BUFR_TEST_DIR
    "${BUFR_TEST_DIR_PATH_LIST}"
)
if (NOT BUFR_TEST_DIR_EXISTS)
    message(WARNING "BUFR test file directory not found -- bufr to ioda tests not generated.")
    set(GENERATE_B2I_TESTS FALSE)
else()
    # message(STATUS "Found bufr test directory: ${BUFR_TEST_DIR}")

    set(OCEAN_BASIN_FILE_ORION "/work/noaa/global/glopara/fix/gdas/soca/20240802/common/RECCAP2_region_masks_all_v20221025.nc")
    set(OCEAN_BASIN_FILE_URSA "/scratch3/NCEPDEV/da/common/validation/RECCAP2_region_masks_all_v20221025.nc")
    set(OCEAN_BASIN_FILE_WCOSS2 "/lfs/h2/emc/da/noscrub/common/validation/RECCAP2_region_masks_all_v20221025.nc")

    set(OCEAN_BASIN_FILE_PATH_LIST
        ${OCEAN_BASIN_FILE_ORION}
        ${OCEAN_BASIN_FILE_URSA}
        ${OCEAN_BASIN_FILE_WCOSS2}
    )
    CHECK_AND_SET_PATH(
        OCEAN_BASIN_FILE
        "${OCEAN_BASIN_FILE_PATH_LIST}"
    )
    if (NOT OCEAN_BASIN_FILE_EXISTS)
        message(WARNING "Ocean basin data file not found -- bufr to ioda tests not generated.")
        set(GENERATE_B2I_TESTS FALSE)
    endif()

	# message(STATUS "Found ocean basin data in ${OCEAN_BASIN_FILE}")
    set(GENERATE_B2I_TESTS TRUE)                                          
endif()


# Function to add b2i tests
function(ADD_B2I_TEST testname testbufr)
	# set(CONFIG_TYPE "json")
    set(CONFIG_TYPE "yaml")

    if (testbufr STREQUAL "mbuoyb") 
        set(DATE "2025061900")
        set(CYCLE "00")
    else()
        if (testbufr STREQUAL "dbuoyb")
            set(DATE "2019010700")
            set(CYCLE "00")
        else()
            set(DATE "2021063006")                                              
            set(CYCLE "06")
        endif()
    endif()

    set(TEST "bufr2ioda_insitu_${testname}")
    set(TESTREF_FILE "${TEST}_${DATE}.ref")
    set(BUFR_INPUT_DIR ${B2I_TEST_DIR})
    set(IODA_OUTPUT_DIR ${B2I_TESTOUTPUT_DIR})
    set(BUFR_TEST_FILE "${DATE}-gdas.t${CYCLE}z.${testbufr}.tm00.bufr_d")
    set(BUFR_FILE "${BUFR_TEST_DIR}/${BUFR_TEST_FILE}")

    if(NOT EXISTS ${BUFR_FILE})
        message(WARNING "BUFR file ${BUFR_FILE} not found; skipping test ${TEST}")
        return()
    endif()
    file(COPY ${BUFR_FILE} DESTINATION ${BUFR_INPUT_DIR})

    set(CONFIG_FILE_NAME "${TEST}_${DATE}.${CONFIG_TYPE}")
    set(CONFIG_FILE_IN "${B2I_TESTINPUT_DIR}/${TEST}_${DATE}.${CONFIG_TYPE}.in")
    set(CONFIG_FILE "${B2I_TEST_DIR}/${CONFIG_FILE_NAME}")
    CREATE_CONFIG_FILE(
		${CONFIG_FILE_IN} 
		${CONFIG_FILE} 
		${BUFR_INPUT_DIR} 
		${IODA_OUTPUT_DIR} 
		${OCEAN_BASIN_FILE}
	)

    add_test(NAME test_b2i_${TEST}
             COMMAND ${B2I_SCRIPT_DIR}/${TEST}.py -c ${CONFIG_FILE} -t ${B2I_TESTREF_DIR}/${TESTREF_FILE}
             WORKING_DIRECTORY ${B2I_TEST_DIR})
    set_property(TEST test_b2i_${TEST}
                 APPEND PROPERTY 
					ENVIRONMENT "PYTHONPATH=${PYIODACONV_DIR}:$ENV{PYTHONPATH}")
	# message("Created test test_b2i_${TEST}")
endfunction()

# Add tests if prerequisites are met
if(GENERATE_B2I_TESTS)
    ADD_B2I_TEST("profile_argo" "subpfl")
    ADD_B2I_TEST("profile_bathy" "bathy")
    ADD_B2I_TEST("profile_glider" "subpfl")
    ADD_B2I_TEST("profile_tesac" "tesac")
    ADD_B2I_TEST("profile_rama" "mbuoyb")
    ADD_B2I_TEST("profile_pirata" "mbuoyb")
    ADD_B2I_TEST("profile_taotriton" "mbuoyb")
    ADD_B2I_TEST("profile_xbtctd" "xbtctd")
    ADD_B2I_TEST("surface_ndbc" "mbuoyb")
    ADD_B2I_TEST("surface_trkob" "trkob")
	ADD_B2I_TEST("surface_dbuoyb_drifter" "dbuoyb")
endif()
