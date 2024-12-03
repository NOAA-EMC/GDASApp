# Function that adds a test for a given GW task
function(add_task task_name test_prefix is_full_cycle HALF_CYCLE FULL_CYCLE pslot WORKING_DIRECTORY PROJECT_SOURCE_DIR)

  # Get subtask names if task is a metatask
  if("${task_name}" STREQUAL "gdas_fcst")
    set(subtask_names_list
      "gdas_fcst_seg0")
  elseif("${task_name}" STREQUAL "enkfgdas_fcst")
    if("${pslot}" STREQUAL "C48mx500_hybAOWCDA")
      set(subtask_names_list
        "enkfgdas_fcst_mem001"
        "enkfgdas_fcst_mem002"
        "enkfgdas_fcst_mem003")
    else()
      set(subtask_names_list
        "enkfgdas_fcst_mem001"
        "enkfgdas_fcst_mem002")
    endif()
  elseif("${task_name}" STREQUAL "gdas_atmos_prod")
    set(subtask_names_list
      "gdas_atmos_prod_f000"
      "gdas_atmos_prod_f001"
      "gdas_atmos_prod_f002"
      "gdas_atmos_prod_f003"
      "gdas_atmos_prod_f004"
      "gdas_atmos_prod_f005"
      "gdas_atmos_prod_f006"
      "gdas_atmos_prod_f007"
      "gdas_atmos_prod_f008"
      "gdas_atmos_prod_f009")
  elseif("${task_name}" STREQUAL "enkfgdas_epmn")
    set(subtask_names_list
      "enkfgdas_epos001"
      "enkfgdas_epos002"
      "enkfgdas_epos003"
      "enkfgdas_epos004"
      "enkfgdas_epos005"
      "enkfgdas_epos006")
  elseif("${task_name}" STREQUAL "enkfgdas_ecmn")
    if ("${pslot}" STREQUAL "C96C48_ufs_hybatmDA")
      set(subtask_names_list
        "enkfgdas_ecen000")
    else()
      set(subtask_names_list
        "enkfgdas_ecen000"
        "enkfgdas_ecen001"
        "enkfgdas_ecen002")
    endif()
  else()
    set(subtask_names_list ${task_name})
  endif()

  # Convert list to comma-delimited string
  string(JOIN "," subtask_names ${subtask_names_list})

  # Get task dependencies
  set(TEST_DEPENDS)
  if(NOT ${is_full_cycle})
    if("${task_name}" STREQUAL "gdas_fcst")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_stage_ic_${HALF_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_atmos_prod")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_fcst_${HALF_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_fcst")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_stage_ic_${HALF_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_echgres")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_fcst_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_fcst_${HALF_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_epmn")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_fcst_${HALF_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_aeroanlgenb")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_fcst_${HALF_CYCLE}")
    else()
      list(APPEND TEST_DEPENDS "${test_prefix}")
    endif()
  else()
    if("${task_name}" STREQUAL "gdas_prep")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_fcst_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_atmos_prod_${HALF_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_anal")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_epmn_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_prep_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_prepatmiodaobs")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_prep_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_atmanlinit")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_epmn_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_prepatmiodaobs_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_atmanlvar")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_atmanlinit_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_atmanlfv3inc")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_atmanlvar_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_atmanlfinal")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_atmanlfv3inc_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_aeroanlinit")
      list(APPEND TEST_DEPENDS "${test_prefix}_aeroanlgenb_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_prep_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_aeroanlvar")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_aeroanlinit_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_aeroanlfinal")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_aeroanlvar_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_snowanl")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_prep_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_sfcanl")
      if("${pslot}" STREQUAL "C96C48_ufs_hybatmDA")
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_atmanlfinal_${FULL_CYCLE}")
      elseif("${pslot}" STREQUAL "C96C48_hybatmaerosnowDA")
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_anal_${FULL_CYCLE}")
        list(APPEND TEST_DEPENDS "${test_prefix}_snowanal_${FULL_CYCLE}")
      else()
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_anal_${FULL_CYCLE}")
      endif()
    elseif("${task_name}" STREQUAL "gdas_analcalc")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_echgres_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_sfcanl_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_fcst")
      if("${pslot}" STREQUAL "C96C48_hybatmaerosnowDA")
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_sfcanl_${FULL_CYCLE}")
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_aeroanlfinal_${FULL_CYCLE}")
      elseif("${pslot}" STREQUAL "C48mx500_3DVarAOWCDA")
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_sfcanl_${FULL_CYCLE}")
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_marineanlfinal_${FULL_CYCLE}")
      else()
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_sfcanl_${FULL_CYCLE}")
      endif()
    elseif("${task_name}" STREQUAL "enkfgdas_atmensanlinit")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_epmn_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_prepatmiodaobs_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_atmensanlobs")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_atmensanlinit_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_atmensanlsol")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_atmensanlobs_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_atmensanlfv3inc")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_atmensanlsol_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_atmensanlfinal")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_atmensanlfv3inc_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_eobs")
      set(TEST_DEPENDS)
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_epmn_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_prep_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_ediag")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_eobs_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_eupd")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_ediag_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_ecmn")
      if("${pslot}" STREQUAL "C96C48_ufs_hybatmDA")
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_analcalc_${FULL_CYCLE}")
        list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_atmensanlfinal_${FULL_CYCLE}")
      else()
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_analcalc_${FULL_CYCLE}")
        list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_eupd_${FULL_CYCLE}")
      endif()
    elseif("${task_name}" STREQUAL "enkfgdas_esnowrecen")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_epmn_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_snowanl_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "enkfgdas_esfc")
      if("${pslot}" STREQUAL "C96C48_ufs_hybatmDA")
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_analcalc_${FULL_CYCLE}")
        list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_atmensanlfinal_${FULL_CYCLE}")
      elseif("${pslot}" STREQUAL "C96C48_hybatmaerosnowDA")
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_analcalc_${FULL_CYCLE}")
        list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_eupd_${FULL_CYCLE}")
        list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_esnowrecen_${FULL_CYCLE}")
      else()
        list(APPEND TEST_DEPENDS "${test_prefix}_gdas_analcalc_${FULL_CYCLE}")
        list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_eupd_${FULL_CYCLE}")
      endif()
    elseif("${task_name}" STREQUAL "enkfgdas_fcst")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_ecmn_${FULL_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_esfc_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_prepoceanobs")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_fcst_${HALF_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_marinebmat")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_fcst_${HALF_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_marineanlinit")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_fcst_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_prepoceanobs_${FULL_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_marinebmat_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_marineanlvar")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_marineanlinit_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_marineanlchkpt")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_marineanlvar_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_marineanlfinal")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_marineanlchkpt_${FULL_CYCLE}")
    elseif("${task_name}" STREQUAL "gdas_marineanlletkf")
      list(APPEND TEST_DEPENDS "${test_prefix}_enkfgdas_fcst_${HALF_CYCLE}")
      list(APPEND TEST_DEPENDS "${test_prefix}_gdas_prepoceanobs_${FULL_CYCLE}")
    else()
      list(APPEND TEST_DEPENDS "${test_prefix}")
    endif()
  endif()

  # Set cycle
  if(${is_full_cycle})
    set(cycle ${FULL_CYCLE})
  else()
    set(cycle ${HALF_CYCLE})
  endif()

  # Add Task
  set(test_name ${test_prefix}_${task_name}_${cycle})
  message(STATUS "preparing ${subtask_names} for ${test_prefix} ctest")
  ecbuild_add_test(TARGET ${test_name}
                   TYPE SCRIPT
                   COMMAND ${PROJECT_SOURCE_DIR}/test/gw-ci/run_exp.sh
                   ARGS ${pslot} ${cycle} ${subtask_names}
                   WORKING_DIRECTORY ${WORKING_DIRECTORY}
                   TEST_DEPENDS ${TEST_DEPENDS})
endfunction()

# Function that generates the 1/2 cycle forecast and DA tasks
function(add_cycling_tests pslot YAML_PATH HOMEgfs WORKING_DIRECTORY PROJECT_SOURCE_DIR HALF_CYCLE_TASKS FULL_CYCLE_TASKS)
  set(test_prefix test_gdasapp_${pslot})
  # Prepare the COMROOT and EXPDIR for the cycling ctests
  ecbuild_add_test(TARGET ${test_prefix}
                   TYPE SCRIPT
                   COMMAND ${PROJECT_SOURCE_DIR}/test/gw-ci/create_exp.sh
                   ARGS ${YAML_PATH} ${pslot} ${HOMEgfs} ${WORKING_DIRECTORY}
                   WORKING_DIRECTORY ${WORKING_DIRECTORY})

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

  # Select the list of tasks to run for the half cycle
  message(STATUS "Half-cycle tasks ${HALF_CYCLE_TASKS}")
  set(is_full_cycle FALSE)
  foreach(task_name ${HALF_CYCLE_TASKS})
    add_task(${task_name} ${test_prefix} ${is_full_cycle} ${HALF_CYCLE} ${FULL_CYCLE} ${pslot} ${WORKING_DIRECTORY} ${PROJECT_SOURCE_DIR})
  endforeach()

  # Select the list of tasks to run for the full cycle
  message(STATUS "Full-cycle tasks ${FULL_CYCLE_TASKS}")
  set(is_full_cycle TRUE)
  foreach(task_name ${FULL_CYCLE_TASKS})
    add_task(${task_name} ${test_prefix} ${is_full_cycle} ${HALF_CYCLE} ${FULL_CYCLE} ${pslot} ${WORKING_DIRECTORY} ${PROJECT_SOURCE_DIR})
  endforeach()
endfunction()

if (WORKFLOW_TESTS)
  # List of tests to run
  option(TEST_GSI "Enable the GFSv17 GSI tests" ON)
  option(TEST_GFS18 "Enable the GFSv18 Atmos JEDI tests" ON)
  option(TEST_AERO_LAND "Enable the GFSv17 Aero-Land JEDI tests" ON)
  option(TEST_MARINE "Enable the GFSv17 Marine JEDI tests" ON)
  option(TEST_GFS17 "Enable the GFSv17 WCDA tests" ON)

  # Setup the environement
  set(HOMEgfs ${CMAKE_SOURCE_DIR}/../../..)
  set(WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/../../test/gw-ci)

  if(${TEST_GSI})
    # GSI Atm DA C96/C48
    # ------------------
    set(pslot "C96C48_hybatmDA")
    set(YAML_PATH ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
    set(HALF_CYCLE_TASKS
      "gdas_stage_ic"
      "gdas_fcst"
      "gdas_atmos_prod"
      "enkfgdas_stage_ic"
      "enkfgdas_fcst"
      "enkfgdas_echgres"
      "enkfgdas_epmn")
    set(FULL_CYCLE_TASKS
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

    add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${WORKING_DIRECTORY} ${PROJECT_SOURCE_DIR} "${HALF_CYCLE_TASKS}" "${FULL_CYCLE_TASKS}")
  endif()  # TEST_GSI

  # JEDI Atm DA C96/C48
  # -------------------
  if(${TEST_GFS18})
    set(pslot "C96C48_ufs_hybatmDA")
    set(YAML_PATH ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
    set(HALF_CYCLE_TASKS
      "gdas_stage_ic"
      "gdas_fcst"
      "gdas_atmos_prod"
      "enkfgdas_stage_ic"
      "enkfgdas_fcst"
      "enkfgdas_echgres"
      "enkfgdas_epmn")
    set(FULL_CYCLE_TASKS
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
    add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${WORKING_DIRECTORY} ${PROJECT_SOURCE_DIR} "${HALF_CYCLE_TASKS}" "${FULL_CYCLE_TASKS}")
  endif()  # TEST_V18

  # Aero-Land DA C96
  # ----------------
  if(${TEST_AERO_LAND})
    set(pslot "C96C48_hybatmaerosnowDA")
    set(YAML_PATH ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
    set(HALF_CYCLE_TASKS
      "gdas_stage_ic"
      "gdas_fcst"
      "gdas_atmos_prod"
      "gdas_aeroanlgenb"
      "enkfgdas_stage_ic"
      "enkfgdas_fcst"
      "enkfgdas_echgres"
      "enkfgdas_epmn")
    set(FULL_CYCLE_TASKS
      "gdas_prep"
      "gdas_anal"
      "gdas_aeroanlinit"
      "gdas_aeroanlvar"
      "gdas_aeroanlfinal"
      "gdas_snowanl"
      "gdas_sfcanl"
      "gdas_analcalc"
      "gdas_fcst"
      "enkfgdas_eobs"
      "enkfgdas_ediag"
      "enkfgdas_eupd"
      "enkfgdas_ecmn"
      "enkfgdas_esnowrecen"
      "enkfgdas_esfc"
      "enkfgdas_fcst"
    )
    add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${WORKING_DIRECTORY} ${PROJECT_SOURCE_DIR} "${HALF_CYCLE_TASKS}" "${FULL_CYCLE_TASKS}")
  endif()  # TEST_AERO_LAND

  if(${TEST_MARINE})
    # GSI Atm DA C48, JEDI Marine DA 500
    # ----------------------------------
    set(pslot "C48mx500_3DVarAOWCDA")
    set(YAML_PATH ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
    set(HALF_CYCLE_TASKS
      "gdas_stage_ic"
      "gdas_fcst")
    set(FULL_CYCLE_TASKS
      "gdas_prepoceanobs"
      "gdas_marinebmat"
      "gdas_marineanlinit"
      "gdas_marineanlvar"
      "gdas_marineanlchkpt"
      "gdas_marineanlfinal"
      # TODO: run the below task once we have a C24/C12 config
      #"gdas_prep"
      #"gdas_anal"
      #"gdas_sfcanl"
      #"gdas_fcst"
      )
    add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${WORKING_DIRECTORY} ${PROJECT_SOURCE_DIR} "${HALF_CYCLE_TASKS}" "${FULL_CYCLE_TASKS}")


    # WCDA, low-res, ensemble da
    # -------------

    set(pslot "C48mx500_hybAOWCDA")
    set(letkf TRUE)
    set(YAML_PATH ${HOMEgfs}/ci/cases/pr/${pslot}.yaml)
    set(HALF_CYCLE_TASKS
      "gdas_stage_ic"
      "gdas_fcst"
      "enkfgdas_stage_ic"
      "enkfgdas_fcst")
    set(FULL_CYCLE_TASKS
      "gdas_prepoceanobs"
      "gdas_marineanlletkf"
      "gdas_marinebmat"
      "gdas_marineanlinit"
      "gdas_marineanlvar"
      "gdas_marineanlchkpt"
      "gdas_marineanlfinal"
      )
    add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${WORKING_DIRECTORY} ${PROJECT_SOURCE_DIR} "${HALF_CYCLE_TASKS}" "${FULL_CYCLE_TASKS}")
    set(letkf FALSE)
  endif()  # TEST_MARINE

  # GFSv17, 3DVAR prototype
  # -----------------------
  if(TEST_GFS17)
    set(pslot "C384mx025_3DVarAOWCDA")
    set(YAML_PATH ${HOMEgfs}/ci/cases/gfsv17/${pslot}.yaml)
    set(HALF_CYCLE_TASKS
      "gdas_stage_ic"
      "gdas_fcst")
    set(FULL_CYCLE_TASKS
      "gdas_prepoceanobs"
      "gdas_marinebmat"
      "gdas_marineanlinit"
      "gdas_marineanlvar"
      "gdas_marineanlchkpt"
      "gdas_marineanlfinal"
      "gdas_ocnanalvrfy"
      "gdas_prep"
      "gdas_anal"
      "gdas_sfcanl"
      "gdas_fcst"
      )
    add_cycling_tests(${pslot} ${YAML_PATH} ${HOMEgfs} ${WORKING_DIRECTORY} ${PROJECT_SOURCE_DIR} "${HALF_CYCLE_TASKS}" "${FULL_CYCLE_TASKS}")
  endif()
endif()
