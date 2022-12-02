# (C) Copyright 2018 UCAR.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

####################################################################
# FLAGS COMMON TO ALL BUILD TYPES
####################################################################

set( CMAKE_Fortran_FLAGS "${CMAKE_Fortran_FLAGS} -fdefault-real-8 -fdefault-double-8 -Waliasing -fcray-pointer -fconvert=big-endian -ffree-line-length-none -fno-range-check -fbacktrace")

####################################################################
# RELEASE FLAGS
####################################################################

set( CMAKE_Fortran_FLAGS_RELEASE "-O3" )

####################################################################
# DEBUG FLAGS
####################################################################

set( CMAKE_Fortran_FLAGS_DEBUG   "-O0 -g -fbounds-check -ffpe-trap=invalid,zero,overflow" )

####################################################################
# BIT REPRODUCIBLE FLAGS
####################################################################

set( CMAKE_Fortran_FLAGS_BIT     "-O2 -fbounds-check" )

####################################################################
# LINK FLAGS
####################################################################

set( CMAKE_Fortran_LINK_FLAGS    "" )

####################################################################

# Meaning of flags
# ----------------
# -fstack-arrays     : Allocate automatic arrays on the stack (needs large stacksize!!!)
# -funroll-all-loops : Unroll all loops
# -fcheck=bounds     : Bounds checking

