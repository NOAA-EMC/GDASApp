SHELL=	/bin/ksh
FC      =$(FCMP)
LIBS    =$(LIBSM)
OBJS	=apply_incr_noahmp_snow.o NoahMPdisag_module.o

CMD     =apply_incr
$(CMD):	$(OBJS)
	${FC} $(FFLAGS) $(OBJS) $(LIBS) -o $(CMD)

NoahMPdisag_module.o: NoahMPdisag_module.f90
	$(FC) $(FFLAGS) -c NoahMPdisag_module.f90

apply_incr_noahmp_snow.o: NoahMPdisag_module.o apply_incr_noahmp_snow.f90
	$(FC) $(FFLAGS) -c apply_incr_noahmp_snow.f90

install:
	-cp -p $(CMD) ../exec/.
clean:
	-rm -f $(OBJS) *.mod $(CMD)
