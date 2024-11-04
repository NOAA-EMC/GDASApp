# Function that adds a test for a given GW task
function(add_task task_name test_prefix cycle pslot RUNTESTS PROJECT_SOURCE_DIR)
  # Get subtask names if task is a metatask
  if("${task_name}" STREQUAL "gdas_fcst")
    set(subtask_names "gdas_fcst_seg0")
  elseif("${task_name}" STREQUAL "enkfgdas_fcst")
    set(subtask_names "enkfgdas_fcst_mem001 enkfgdas_fcst_mem002")
  elseif("${task_name}" STREQUAL "gdas_atmos_prod")
    set(subtask_names "gdas_atmos_prod_f000 gdas_atmos_prod_f001 gdas_atmos_prod_f002 gdas_atmos_prod_f003 gdas_atmos_prod_f004 gdas_atmos_prod_f005 gdas_atmos_prod_f006 gdas_atmos_prod_f007 gdas_atmos_prod_f008 gdas_atmos_prod_f009")
  elseif("${task_name}" STREQUAL "enkfgdas_epmn")
    set(subtask_names "enkfgdas_epos001 enkfgdas_epos002 enkfgdas_epos003 enkfgdas_epos004 enkfgdas_epos005 enkfgdas_epos006")
  elseif("${task_name}" STREQUAL "enkfgdas_ecmn")
    set(subtask_names "enkfgdas_ecen000")
  else()
    set(subtask_names ${task_name})
  endif()

  # Add Task
  set(test_name ${test_prefix}_${task_name}_${cycle})
  message(STATUS "preparing ${subtask_names} for ${test_prefix} ctest")
  add_test(NAME ${test_name}
           COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh ${pslot} ${cycle} ${subtask_names}"
           WORKING_DIRECTORY ${RUNTESTS})
  set_tests_properties(${test_name} PROPERTIES LABELS "manual")
endfunction()

# Function that generates the 1/2 cycle forecast and DA tasks
function(add_cycling_tests pslot YAML_PATH HOMEgfs RUNTESTS PROJECT_SOURCE_DIR TASK_LIST)
  set(test_prefix test_gdasapp_${pslot})
  # Prepare the COMROOT and EXPDIR for the cycling ctests
  add_test(NAME ${test_prefix}
    COMMAND /bin/bash -c "${PROJECT_SOURCE_DIR}/test/gw-ci/create_exp.sh ${YAML_PATH} ${pslot} ${HOMEgfs} ${RUNTESTS}"
    WORKING_DIRECTORY ${RUNTESTS})
  set_tests_properties(${test_prefix} PROPERTIES LABELS "manual")

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

  # Half cycle tasks common to all CI tests
  add_task("gdas_stage_ic"     ${test_prefix} ${HALF_CYCLE} ${pslot} ${RUNTESTS} ${PROJECT_SOURCE_DIR})
  add_task("gdas_fcst"         ${test_prefix} ${HALF_CYCLE} ${pslot} ${RUNTESTS} ${PROJECT_SOURCE_DIR})

  # Half cycle task commot to all CI test except C48mx500_3DVarAOWCDA
  if(NOT pslot STREQUAL "C48mx500_3DVarAOWCDA")
    add_task("enkfgdas_stage_ic" ${test_prefix} ${HALF_CYCLE} ${pslot} ${RUNTESTS} ${PROJECT_SOURCE_DIR})
    add_task("enkfgdas_fcst"     ${test_prefix} ${HALF_CYCLE} ${pslot} ${RUNTESTS} ${PROJECT_SOURCE_DIR})
    add_task("enkfgdas_echgres"  ${test_prefix} ${HALF_CYCLE} ${pslot} ${RUNTESTS} ${PROJECT_SOURCE_DIR})
    add_task("enkfgdas_epmn"     ${test_prefix} ${HALF_CYCLE} ${pslot} ${RUNTESTS} ${PROJECT_SOURCE_DIR})
    add_task("gdas_atmos_prod"   ${test_prefix} ${HALF_CYCLE} ${pslot} ${RUNTESTS} ${PROJECT_SOURCE_DIR})
  endif()
  
  # Half cycle tasks unique to C96C48_hybatmaerosnowDA
  if(pslot STREQUAL "C96C48_hybatmaerosnowDA")
    add_task("gdas_aeroanlgenb" ${test_prefix} ${HALF_CYCLE} ${pslot} ${RUNTESTS} ${PROJECT_SOURCE_DIR})
  endif()

  # Select the list of tasks to run for the full cycle
  message(STATUS "Tasks ${TASK_LIST}")
  foreach(task_name ${TASK_LIST})
    add_task(${task_name} ${test_prefix} ${FULL_CYCLE} ${pslot} ${RUNTESTS} ${PROJECT_SOURCE_DIR})
  endforeach()
endfunction()

option(RUN_GW_CI "Enable the global-workflow CI tests" OFF)
if (RUN_GW_CI)
  # Setup the environement
  set(HOMEgfs ${CMAKE_SOURCE_DIR}/../../..)
  set(RUNTESTS ${CMAKE_CURRENT_BINARY_DIR}/../../test/gw-ci)
  
  # GSI Atm DA C96/C48
  # ------------------
  set(pslot "C96C48_hybatmDA")
  set(YAML_PATH ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
  set(TASK_LIST
    "gdas_prep"
    "gdas_anal"
    "gdas_sfcanl"
    "gdas_analcalc"
    "gdas_fcst"
    "enkfgdas_eobs"
    "enkfgdas_ediag"
    "enkfgdas_eupd"
    "enkfgdas_ecmn"
    "enkfgdas_esfc"
    "enkfgdas_fcst"
  )
  add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${RUNTESTS} ${PROJECT_SOURCE_DIR} "${TASK_LIST}")

  # JEDI Atm DA C96/C48
  # -------------------
  set(pslot "C96C48_ufs_hybatmDA")
  set(YAML_PATH ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
  set(TASK_LIST
    "gdas_prep"
    "gdas_prepatmiodaobs"
    "gdas_atmanlinit"
    "gdas_atmanlvar"
    "gdas_atmanlfv3inc"
    "gdas_atmanlfinal"
    "gdas_sfcanl"
    "gdas_analcalc"
    "gdas_fcst"
    "enkfgdas_atmensanlinit"
    "enkfgdas_atmensanlobs"
    "enkfgdas_atmensanlsol"
    "enkfgdas_atmensanlfv3inc"
    "enkfgdas_atmensanlfinal"
    "enkfgdas_ecmn"
    "enkfgdas_esfc"
    "enkfgdas_fcst"
  )
  add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${RUNTESTS} ${PROJECT_SOURCE_DIR} "${TASK_LIST}")  

  # Aero-Land DA C96
  # ----------------
  set(pslot "C96C48_hybatmaerosnowDA")
  set(YAML_PATH ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
  set(TASK_LIST
    "gdas_prep"
    "gdas_anal"
    "gdas_prepsnowobs"
    "gdas_snowanl"
    "gdas_aeroanlgenb"
    "gdas_aeroanlinit"
    "gdas_aeroanlvar"
    "gdas_aeroanlfinal"
    "gdas_sfcanl"
    "gdas_analcalc"
    "gdas_fcst"
    "enkfgdas_eobs"
    "enkfgdas_ediag"
    "enkfgdas_eupd"
    "enkfgdas_ecmn"
    "enkfgdas_esfc"
    "enkfgdas_fcst"
  )
  add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${RUNTESTS} ${PROJECT_SOURCE_DIR} "${TASK_LIST}")
  
  # GSI Atm DA C48, JEDI Marine DA 500
  # ----------------------------------
  set(pslot "C48mx500_3DVarAOWCDA")
  set(YAML_PATH ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
  set(TASK_LIST
    "gdas_prep"
    "gdas_anal"
    "gdas_prepoceanobs"
    "gdas_marinebmat"
    "gdas_marineanlinit"
    "gdas_marineanlvar"
    "gdas_marineanlchkpt"
    "gdas_marineanlfinal"
    "gdas_ocnanalvrfy"
    "gdas_sfcanl"
    "gdas_fcst"
    )
  add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${RUNTESTS} ${PROJECT_SOURCE_DIR} "${TASK_LIST}")
endif()
