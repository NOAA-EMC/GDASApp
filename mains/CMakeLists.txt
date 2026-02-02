# Build the big gdas executable used for all generic JEDI applications
# --------------------------------------------------------------------
if (BUILD_SOCA)
  ecbuild_add_executable( TARGET  gdas.x
                          SOURCES gdas.cc
                          LIBS    fv3jedi soca
                        )
  # Add preprocessor definition if BUILD_SOCA is enabled
  target_compile_definitions(gdas.x PRIVATE BUILD_SOCA)
else()
  ecbuild_add_executable( TARGET  gdas.x
                          SOURCES gdas.cc
                          LIBS    fv3jedi
                        )
endif()

if (BUILD_SOCA)
# Build the soca executables that are not OOPS-based
# --------------------------------------------------
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

ecbuild_add_executable( TARGET  gdas_soca_anpproc.x
	                SOURCES ${CMAKE_SOURCE_DIR}/soca/src/mains/AnalysisPostproc.cc
			LIBS    soca
		      )
endif()

ecbuild_add_executable( TARGET  gdas_fv3jedi_error_covariance_toolbox.x
                        SOURCES ${CMAKE_SOURCE_DIR}/fv3-jedi/src/mains/fv3jediErrorCovarianceToolbox.cc
                        LIBS    fv3jedi saber
                      )
