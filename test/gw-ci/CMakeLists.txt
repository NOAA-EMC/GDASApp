# Function that generates the 1/2 cycle forecast and DA tasks
function(add_cycling_tests pslot YAML_PATH HOMEgfs RUNTESTS PROJECT_SOURCE_DIR TASK_LIST)
  set(test_name test_gdasapp_${pslot})
  # Prepare the COMROOT and EXPDIR for the cycling ctests
  add_test(NAME ${test_name}
    COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/create_exp.sh ${YAML_PATH} ${pslot} ${HOMEgfs} ${RUNTESTS}"
    WORKING_DIRECTORY ${RUNTESTS})
  set_tests_properties(${test_name} PROPERTIES LABELS "manual")

  # Get the 1/2 cycle and full cycle's dates
  execute_process(
    COMMAND ${CMAKE_COMMAND} -E env python ${PROJECT_SOURCE_DIR}/test/gw-ci/get_cycles.py ${YAML_PATH}
    OUTPUT_VARIABLE SCRIPT_OUTPUT
    RESULT_VARIABLE SCRIPT_RESULT
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )
  string(REPLACE "," ";" DATES_LIST ${SCRIPT_OUTPUT})
  list(GET DATES_LIST 0 HALF_CYCLE)
  list(GET DATES_LIST 1 FULL_CYCLE)

  # stage IC's
  message(STATUS "staging the 1/2 cycle IC's for ${pslot} ctest")
  add_test(NAME ${test_name}_gdas_stage_ic_${HALF_CYCLE}
           COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh ${pslot} gdas_stage_ic ${HALF_CYCLE}"
           WORKING_DIRECTORY ${RUNTESTS})
  set_tests_properties(${test_name}_gdas_stage_ic_${HALF_CYCLE} PROPERTIES LABELS "manual")

  # stage ensemble ics
  if (letkf)
    message(STATUS "preparing enkfgdas_stage_ic for ${pslot} ctest")
    add_test(NAME ${test_name}_enkfgdas_stage_ic_${HALF_CYCLE}
             COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh ${pslot} enkfgdas_stage_ic ${HALF_CYCLE}"
             WORKING_DIRECTORY ${RUNTESTS})
    set_tests_properties(${test_name}_enkfgdas_stage_ic_${HALF_CYCLE} PROPERTIES LABELS "manual")
  endif()

  # 1/2 cycle gdas_fcst
  message(STATUS "preparing 1/2 cycle gdas_fcst for ${pslot} ctest")
  add_test(NAME ${test_name}_gdas_fcst_seg0_${HALF_CYCLE}
           COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh ${pslot} gdas_fcst_seg0 ${HALF_CYCLE}"
           WORKING_DIRECTORY ${RUNTESTS})
  set_tests_properties(${test_name}_gdas_fcst_seg0_${HALF_CYCLE} PROPERTIES LABELS "manual")

  # 1/2 cycle enkfgdas_fcst
  if (letkf)
    set(ENS_MEMS  "mem001" "mem002" "mem003")
    foreach(ENS_MEM ${ENS_MEMS})
      message(STATUS "preparing 1/2 cycle enkfgdas_fcst_${ENS_MEM} for ${pslot} ctest")
        add_test(NAME ${test_name}_enkfgdas_fcst_${ENS_MEM}_${HALF_CYCLE}
                 COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh ${pslot} enkfgdas_fcst_${ENS_MEM} ${HALF_CYCLE}"
                 WORKING_DIRECTORY ${RUNTESTS})
        set_tests_properties(${test_name}_enkfgdas_fcst_${ENS_MEM}_${HALF_CYCLE} PROPERTIES LABELS "manual")
    endforeach()
  endif()

  # Select the list of tasks to run for the full cycle
  message(STATUS "Tasks ${TASK_LIST}")

  foreach(task ${TASK_LIST})
    message(STATUS "preparing the full cycle ${task} for ${pslot} ctest")
    add_test(NAME ${test_name}_${task}_${FULL_CYCLE}
             COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh ${pslot} ${task} ${FULL_CYCLE}"
             WORKING_DIRECTORY ${RUNTESTS})
    set_tests_properties(${test_name}_${task}_${FULL_CYCLE} PROPERTIES LABELS "manual")
  endforeach()
endfunction()

if (WORKFLOW_TESTS)
  # Setup the environement
  set(HOMEgfs ${CMAKE_SOURCE_DIR}/../../..)
  set(RUNTESTS ${CMAKE_CURRENT_BINARY_DIR}/../../test/gw-ci)

  # 3DVAR WCDA, low-res
  # -------------------
  set(pslot "WCDA-3DVAR-C48mx500")
  set(YAML_PATH ${HOMEgfs}/ci/cases/pr/C48mx500_3DVarAOWCDA.yaml)
  set(TASK_LIST
    "gdas_prepoceanobs"
    "gdas_marinebmat"
    "gdas_marineanlinit"
    "gdas_marineanlvar"
    "gdas_marineanlchkpt"
    "gdas_marineanlfinal"
    )
  add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${RUNTESTS} ${PROJECT_SOURCE_DIR} "${TASK_LIST}")

  # WCDA, low-res, ensemble da
  # -------------
  set(pslot "WCDA-hyb-C48mx500")
  set(letkf TRUE)
  set(YAML_PATH ${HOMEgfs}/ci/cases/pr/C48mx500_hybAOWCDA.yaml)
  set(TASK_LIST
    "gdas_prepoceanobs"
    "gdas_marineanlletkf"
    # TODO(AFE) waiting until these are working for hybrid
    # "gdas_marinebmat"
    # "gdas_marineanlinit"
    # "gdas_marineanlvar"
    # "gdas_marineanlchkpt"
    # "gdas_marineanlfinal"
    )
  add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${RUNTESTS} ${PROJECT_SOURCE_DIR} "${TASK_LIST}")
  set(letkf FALSE)
endif()

option(RUN_GW_CI "Enable the global-workflow CI tests" OFF)
if (RUN_GW_CI)
  # Aero-Land DA, C96
  # -----------------
  set(pslot "Aero-Snow-3DVAR-C96")
  set(YAML_PATH ${HOMEgfs}/ci/cases/pr/C96C48_hybatmaerosnowDA.yaml)
  set(TASK_LIST)  # empty list for now
  add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${RUNTESTS} ${PROJECT_SOURCE_DIR} "${TASK_LIST}")

  # Atm DA, C96/C48
  # ---------------
  set(pslot "Atm-hyb-C96C48")
  set(YAML_PATH ${HOMEgfs}/ci/cases/pr/C96C48_ufs_hybatmDA.yaml)
  set(TASK_LIST)  # empty list for now
  add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${RUNTESTS} ${PROJECT_SOURCE_DIR} "${TASK_LIST}")

  # GFSv17, 3DVAR prototype
  # -----------------------
  set(pslot "GFSv17-3DVAR-C384mx025")
  set(YAML_PATH ${HOMEgfs}/ci/cases/gfsv17/C384mx025_3DVarAOWCDA.yaml)
  set(TASK_LIST
    "gdas_prepoceanobs"
    "gdas_marinebmat"
    "gdas_marineanlinit"
    "gdas_marineanlvar"
    "gdas_marineanlchkpt"
    "gdas_marineanlfinal"
    "gdas_ocnanalvrfy"
    "gdas_prep"
    "gdas_anal"
    )
  add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${RUNTESTS} ${PROJECT_SOURCE_DIR} "${TASK_LIST}")
endif()
