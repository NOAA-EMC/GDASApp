ecbuild_add_executable( TARGET  gdas_fv3jedi.x
                        SOURCES gdas_fv3jedi.cc
                        LIBS    fv3jedi
                      )

ecbuild_add_executable( TARGET  gdas_soca.x
                        SOURCES gdas_soca.cc
                        LIBS    soca
                      )
