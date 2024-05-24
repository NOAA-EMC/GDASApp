# Setup the environement
set(HOMEgfs ${CMAKE_SOURCE_DIR}/../../..)
set(RUNTESTS ${CMAKE_CURRENT_BINARY_DIR}/../../test/gw-ci)

# List of g-w ci test to create
# -----------------------------
set(cycling_tests "C48mx500_3DVarAOWCDA" "C96_atmaerosnowDA" "C96C48_ufs_hybatmDA")

# List of tasks to run for each test
# ----------------------------------
set(C48mx500_3DVarAOWCDA_tasks
  "gdasprepoceanobs"
  "gdasocnanalprep"
  "gdasocnanalbmat"
  "gdasocnanalrun"
  "gdasocnanalchkpt"
  "gdasocnanalpost")
set(C96_atmaerosnowDA_tasks)     # empty list for now
set(C96C48_ufs_hybatmDA_tasks)   # empty list for now

# Iterate through the list of cycling test
# ----------------------------------------
foreach(pslot ${cycling_tests})
  message(STATUS "preparing ${pslot} ctest")
  # Prepare the COMROOT and EXPDIR for the cycling ctests
  set(YAML ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
  add_test(NAME ${pslot}
    COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/create_exp.sh ${YAML} ${pslot} ${HOMEgfs} ${RUNTESTS}"
    WORKING_DIRECTORY ${RUNTESTS})
  set_tests_properties(${pslot} PROPERTIES LABELS "manual")

  # Get the 1/2 cycle and full cycle's dates
  execute_process(
    COMMAND ${CMAKE_COMMAND} -E env python ${PROJECT_SOURCE_DIR}/test/gw-ci/get_cycles.py ${YAML}
    OUTPUT_VARIABLE SCRIPT_OUTPUT
    RESULT_VARIABLE SCRIPT_RESULT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    )
  string(REPLACE "," ";" DATES_LIST ${SCRIPT_OUTPUT})
  list(GET DATES_LIST 0 HALF_CYCLE)
  list(GET DATES_LIST 1 FULL_CYCLE)

  # 1/2 cycle gdasfcst
  message(STATUS "preparing 1/2 cycle gdasfcst for ${pslot} ctest")
  add_test(NAME ${pslot}_gdasfcst_${HALF_CYCLE}
           COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh ${pslot} gdasfcst ${HALF_CYCLE}"
           WORKING_DIRECTORY ${RUNTESTS})
  set_tests_properties(${pslot}_gdasfcst_${HALF_CYCLE} PROPERTIES LABELS "manual")

  # Select the list of tasks to run for the full cycle
  set(TASK_LIST_NAME "${pslot}_tasks")
  set(TASK_LIST "${${TASK_LIST_NAME}}")
  message(STATUS "Tasks for ${EXPERIMENT}: ${TASK_LIST}")

  foreach(task ${TASK_LIST})
    message(STATUS "preparing the full cycle ${task} for ${pslot} ctest")
    add_test(NAME ${pslot}_${task}_${FULL_CYCLE}
             COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh ${pslot} ${task} ${FULL_CYCLE}"
             WORKING_DIRECTORY ${RUNTESTS})
    set_tests_properties(${pslot}_${task}_${FULL_CYCLE} PROPERTIES LABELS "manual")
  endforeach()
endforeach()
