# test for creating an experiment directory within the global-workflow
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/testrun)

# Prepare ROTDIR and static dir
add_test(NAME test_gdasapp_soca_prep
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/gw/prep.sh ${PROJECT_BINARY_DIR} ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw)
       set_tests_properties(test_gdasapp_soca_prep
      PROPERTIES
      ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/ush:${PROJECT_SOURCE_DIR}/../../ush/python/wxflow:$ENV{PYTHONPATH}")

# Identify machine
set(MACHINE "container")
IF (IS_DIRECTORY /work2)
  string(SUBSTRING $ENV{HOSTNAME} 0 8 HOST)
  IF ("${HOST}" STREQUAL "hercules")
    set(MACHINE "hercules")
    set(PARTITION "hercules")
  ELSE()
    set(MACHINE "orion")
    set(PARTITION "orion")
  ENDIF()
ENDIF()
IF (IS_DIRECTORY /scratch2/NCEPDEV/)
  set(MACHINE "hera")
  set(PARTITION "hera")
ENDIF()

# Clean-up
add_test(NAME test_gdasapp_soca_run_clean
  COMMAND  ${CMAKE_COMMAND} -E remove_directory ${PROJECT_BINARY_DIR}/test/soca/gw/testrun/testjjobs)

# Create scratch for testing apps
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/apps_scratch)

# Create scratch for obs prep task
file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/obsprep)

# Set up obsprep, based on test_gdasapp_util_prepdata
add_test(NAME test_gdasapp_soca_setup_obsprep
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/gw/setup_obsprep.sh ${PROJECT_SOURCE_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/obsprep)

# Test JGDAS_GLOBAL_OCEAN_ANALYSIS_*
set(jjob_list "JGLOBAL_PREP_OCEAN_OBS"
              "JGLOBAL_MARINE_BMAT"
              "JGDAS_GLOBAL_OCEAN_ANALYSIS_PREP"
#              "JGDAS_GLOBAL_OCEAN_ANALYSIS_BMAT"
              "JGDAS_GLOBAL_OCEAN_ANALYSIS_RUN"
#              "JGDAS_GLOBAL_OCEAN_ANALYSIS_ECEN"
	      "JGLOBAL_MARINE_ANALYSIS_LETKF"
              "JGDAS_GLOBAL_OCEAN_ANALYSIS_CHKPT"
	      "JGDAS_GLOBAL_OCEAN_ANALYSIS_POST")
# Temporary Removal while fixing/improving vrfy task
#              "JGDAS_GLOBAL_OCEAN_ANALYSIS_VRFY")

set(setup "")
foreach(jjob ${jjob_list})

  # Make a copy of the scratch before it is removed by post
  IF (jjob STREQUAL "JGDAS_GLOBAL_OCEAN_ANALYSIS_CHKPT")
    add_test(NAME test_gdasapp_soca_copy_scratch
         COMMAND ${PROJECT_SOURCE_DIR}/test/soca/gw/copy_scratch.sh ${PROJECT_BINARY_DIR}
         WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw)
  ENDIF()


  # substitute a few variables in the test yaml
  message("ctest for ${jjob}")
  set(HOMEgfs ${PROJECT_SOURCE_DIR}/../..)
  set(JJOB ${jjob})
  configure_file(${PROJECT_SOURCE_DIR}/test/soca/gw/run_jjobs.yaml.test
                 ${PROJECT_BINARY_DIR}/test/soca/gw/testrun/run_jjobs_${jjob}.yaml)
  set(test_name "test_gdasapp_soca_${jjob}")
  add_test(NAME ${test_name}
    COMMAND ${PROJECT_SOURCE_DIR}/ush/soca/run_jjobs.py
         -y ${PROJECT_BINARY_DIR}/test/soca/gw/testrun/run_jjobs_${jjob}.yaml
         ${setup}
    WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/testrun)
  set_tests_properties(${test_name}
    PROPERTIES
    ENVIRONMENT "PYTHONPATH=${PROJECT_SOURCE_DIR}/ush/ioda/bufr2ioda::${PROJECT_SOURCE_DIR}/ush:${PROJECT_BINARY_DIR}/../lib/python${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}:${PROJECT_SOURCE_DIR}/ush/soca:${PROJECT_SOURCE_DIR}/../../../../ush/python:$ENV{PYTHONPATH}")


  set(setup "--skip") # Only run the setup of the first test, if not, it will hang
                      # waiting for standard input from setup_expt.py
endforeach()

# Test gdas/oops applications
# add ens_handler back to the list when testing ensemble DA again
foreach(ctest ${ctest_list})
  set(TEST ${ctest})
  set(EXEC ${PROJECT_BINARY_DIR}/../bin/gdas_${ctest}.x)
  set(YAML ${PROJECT_SOURCE_DIR}/test/soca/testinput/${ctest}.yaml)
  configure_file(${PROJECT_SOURCE_DIR}/test/soca/gw/run_gdas_apps.yaml.test
                 ${PROJECT_BINARY_DIR}/test/soca/gw/testrun/run_gdas_apps_${ctest}.yaml)
  set(test_name "test_gdasapp_soca_${ctest}")
  add_test(NAME ${test_name}
      COMMAND ${PROJECT_SOURCE_DIR}/ush/soca/run_jjobs.py
           -y ${PROJECT_BINARY_DIR}/test/soca/gw/testrun/run_gdas_apps_${ctest}.yaml
           --skip --ctest True
      WORKING_DIRECTORY ${PROJECT_BINARY_DIR}/test/soca/gw/apps_scratch)

  set_tests_properties(${test_name}
      PROPERTIES
      ENVIRONMENT "PYTHONPATH=${PROJECT_BINARY_DIR}/../lib/python${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}:$ENV{PYTHONPATH}")
endforeach()
