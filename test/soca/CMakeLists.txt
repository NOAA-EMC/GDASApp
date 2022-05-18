# Create a test R2D2 database for obs
# -----------------------------------
set( OBS_DIR ${PROJECT_BINARY_DIR}/test/testdata )
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obs)
ecbuild_add_test(
      TARGET    test_gdasapp_soca_obsdb
      TYPE      SCRIPT
      COMMAND   ${Python3_EXECUTABLE}
      ARGS      ${PROJECT_SOURCE_DIR}/test/soca/create_obsdb.py
      WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/obs
      ENVIRONMENT
        OBS_DIR=${OBS_DIR}
        PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH}
)

# Prepare backgrounds
# -------------------
# 1 - create fake 3 hourly restarts under RESTART
# 2 - store them with R2D2
set( TESTDATA ${PROJECT_BINARY_DIR}/test/testdata )
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/bkg)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/bkg/RESTART)
ecbuild_add_test(
      TARGET    test_gdasapp_soca_bkgdb
      TYPE      SCRIPT
      COMMAND   ${Python3_EXECUTABLE}
      ARGS      ${PROJECT_SOURCE_DIR}/test/soca/create_bkgdb.py
      WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/bkg
      ENVIRONMENT
        TESTDATA=${TESTDATA}
        PYTHONPATH=${PROJECT_BINARY_DIR}/ush:$ENV{PYTHONPATH}
)

# Symlink test input yaml files
# -----------------------------
# create testinput dir
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/testinput)

# list of test input files to install
list(APPEND test_input
  ${PROJECT_SOURCE_DIR}/parm/soca/obs/obs_list.yaml
  ${PROJECT_SOURCE_DIR}/test/soca/testinput/dumy.yaml
)

# symlink
foreach(FILENAME ${test_input})
  get_filename_component(filename ${FILENAME} NAME )
  execute_process( COMMAND ${CMAKE_COMMAND} -E create_symlink
           ${FILENAME}
           ${PROJECT_BINARY_DIR}/test/soca/testinput/${filename} )
endforeach(FILENAME)

# install
install(FILES ${test_input}
        DESTINATION "test/testinput/")

# Set runtime environement variables
# ----------------------------------
set( CDATE 2018041512 )        # Analysis date
set( GDATE 2018041509 )        # Guess date ... Still ... what's that?
set( assim_freq 6 )            # DA window
set( COMOUT ${CMAKE_CURRENT_BINARY_DIR}/3dvar )
set( COMIN_OBS ${CMAKE_CURRENT_BINARY_DIR}/obs/r2d2-shared )
set( COMIN_GES ${CMAKE_CURRENT_BINARY_DIR}/bkg )  # Backgrounds from previous forecast
set( CASE "12345" )                               # TODO: No idea what this is, figure it out!
set( CASE_ENKF "123456")                          # TODO: No idea what this is, figure it out!
set( LEVS "75" )                                  # TODO: I can sort of guess ...
# TODO: Consolidate the OBS_* envar below
set( OBS_LIST "adt_j3 sst_noaa19_l3u icec_EMC icefb_GDR temp_profile_fnmoc salt_profile_fnmoc" )
set( OBS_YAML ${CMAKE_CURRENT_BINARY_DIR}/testinput/obs_list.yaml ) # TODO: Is that the list of obs
set( OBS_YAML_DIR ${PROJECT_SOURCE_DIR}/parm/soca/obs/config ) # TODO: Is that the list of obs
                                                                   #       for the experiment?
set( HOMEgfs ${PROJECT_SOURCE_DIR} )                                      # TODO: Where the bundle src is?
set( STATICB_DIR ${CMAKE_CURRENT_BINARY_DIR}/staticb )                    # Overrated things to do DA
set( FV3JEDI_STAGE_YAML ${CMAKE_CURRENT_BINARY_DIR}/testinput/dumy.yaml ) # Useless atmospheric stuff
set( R2D2_OBS_DB shared )
set( R2D2_OBS_DUMP soca )
set( R2D2_OBS_SRC gdasapp )
set( R2D2_OBS_WINDOW 24 )     # Not the samne as the DA window!
set( R2D2_WINDOW_BEGIN 2018041500 )

# Create a working directory for prep/run/post
# --------------------------------------------
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/3dvar)

# Prep
ecbuild_add_test(
      TARGET    test_gdasapp_soca_ana_prep
      TYPE      SCRIPT
      COMMAND   ${Python3_EXECUTABLE}
      ARGS      ${PROJECT_SOURCE_DIR}/scripts/exgdas_global_marine_analysis_prep.py
      WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/3dvar
      ENVIRONMENT
        COMOUT=${COMOUT}
        COMIN_OBS=${COMIN_OBS}
        COMIN_GES=${COMIN_GES}
        CASE=${CASE}
        CASE_ENKF=${CASE_ENKF}
        LEVS=${LEVS}
        HOMEgfs=${HOMEgfs}
        CDATE=${CDATE}
        GDATE=${GDATE}
        assim_freq=${assim_freq}
        STATICB_DIR=${STATICB_DIR}
        OBS_YAML=${OBS_YAML}
        OBS_YAML_DIR=${OBS_YAML_DIR}
        FV3JEDI_STAGE_YAML=${FV3JEDI_STAGE_YAML}
        R2D2_OBS_DB=${R2D2_OBS_DB}
        R2D2_OBS_DUMP=${R2D2_OBS_DUMP}
        R2D2_OBS_SRC=${R2D2_OBS_SRC}
        R2D2_OBS_WINDOW=${R2D2_OBS_WINDOW}
        R2D2_WINDOW_BEGIN=${R2D2_WINDOW_BEGIN}
)
