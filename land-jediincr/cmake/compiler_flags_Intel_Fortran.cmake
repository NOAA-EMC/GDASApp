# (C) Copyright 2018 UCAR.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

####################################################################
# FLAGS COMMON TO ALL BUILD TYPES
####################################################################

set( CMAKE_Fortran_FLAGS "${CMAKE_Fortran_FLAGS} -convert big_endian -fno-alias -auto -safe-cray-ptr -ftz -assume byterecl -i4 -r8 -nowarn -sox -traceback -msse2" )

####################################################################
# RELEASE FLAGS
####################################################################

set( CMAKE_Fortran_FLAGS_RELEASE "-O3 -debug minimal -fp-model source" )

####################################################################
# DEBUG FLAGS
####################################################################

set( CMAKE_Fortran_FLAGS_DEBUG   "-g -O0 -check -check noarg_temp_created -check nopointer -warn -warn noerrors -fpe0 -ftrapuv" )

####################################################################
# BIT REPRODUCIBLE FLAGS
####################################################################

set( CMAKE_Fortran_FLAGS_BIT     "-O2 -debug minimal -fp-model source" )

####################################################################
# LINK FLAGS
####################################################################

set( CMAKE_Fortran_LINK_FLAGS    "" )

####################################################################

# Meaning of flags
# ----------------
# todo

