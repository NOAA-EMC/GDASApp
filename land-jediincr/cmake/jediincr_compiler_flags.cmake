# (C) Copyright 2018 UCAR.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

#add_definitions ( -Duse_libMPI -Duse_netCDF -DSPMD -DNXGLOB=4)
add_definitions ( -Duse_libMPI -Duse_netCDF -Dncdf -Dgather_scatter_barrier)

#######################################################################################
# Fortran
#######################################################################################

if( CMAKE_Fortran_COMPILER_ID MATCHES "GNU" )
  include( compiler_flags_GNU_Fortran )
elseif( CMAKE_Fortran_COMPILER_ID MATCHES "Intel" )
  include( compiler_flags_Intel_Fortran )
elseif( CMAKE_Fortran_COMPILER_ID MATCHES "XL" )
  include( compiler_flags_XL_Fortran )
elseif( CMAKE_Fortran_COMPILER_ID MATCHES "Cray" )
  include( compiler_flags_Cray_Fortran )
else()
  message( STATUS "Fortran compiler with ID ${CMAKE_Fortran_COMPILER_ID} will be used with CMake default options")
endif()
