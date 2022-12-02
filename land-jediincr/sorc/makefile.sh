#!/bin/ksh
set -x
#-----------------------------------------------------
#-use standard module.
#-----------------------------------------------------

#export INCS=${NETCDF_INCLUDE}             # netcdf_parallel module sets this
export INCS="-I${NETCDF}/include"          # netcdf modules does not 
export FFLAGS="$INCS -O3 -fp-model precise -r8 -convert big_endian -traceback -g"

#export LIBSM="${NETCDF_LDFLAGS_F}"        # as above
export LIBSM="-L${NETCDF}/lib -lnetcdff"

make -f Makefile clean
make -f Makefile
make -f Makefile install
make -f Makefile clean
