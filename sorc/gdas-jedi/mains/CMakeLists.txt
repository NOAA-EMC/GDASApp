# Build the big gdas executable used for all generic JEDI applications
# --------------------------------------------------------------------
ecbuild_add_executable( TARGET  gdas.x
                        SOURCES gdas.cc
                        LIBS    fv3jedi soca
                      )

# Build the model executables that are not OOPS-based
# ---------------------------------------------------
ecbuild_add_executable( TARGET  gdas_soca_gridgen.x
                        SOURCES ${CMAKE_SOURCE_DIR}/soca/src/mains/GridGen.cc
                        LIBS    soca
                      )

ecbuild_add_executable( TARGET  gdas_soca_error_covariance_toolbox.x
                        SOURCES ${CMAKE_SOURCE_DIR}/soca/src/mains/ErrorCovarianceToolbox.cc
                        LIBS    soca saber
                      )

ecbuild_add_executable( TARGET  gdas_soca_setcorscales.x
                        SOURCES ${CMAKE_SOURCE_DIR}/soca/src/mains/SetCorScales.cc
                        LIBS    soca
                      )

ecbuild_add_executable( TARGET  gdas_fv3jedi_error_covariance_toolbox.x
                        SOURCES ${CMAKE_SOURCE_DIR}/fv3-jedi/src/mains/fv3jediErrorCovarianceToolbox.cc
                        LIBS    fv3jedi saber
                      )
