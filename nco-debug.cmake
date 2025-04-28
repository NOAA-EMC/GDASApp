set(CMAKE_Fortran_FLAGS "-ftrapuv -g -traceback -check all,noarg_temp_created ${CMAKE_Fortran_FLAGS}" CACHE STRING "Fortran flags" FORCE)
set(CMAKE_C_FLAGS "-ftrapuv -g -traceback -check=uninit ${CMAKE_C_FLAGS}" CACHE STRING "C flags" FORCE)
set(CMAKE_CXX_FLAGS "-ftrapuv -g -traceback -check=uninit ${CMAKE_CXX_FLAGS}" CACHE STRING "C++ flags" FORCE)
