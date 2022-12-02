 program apply_incr_noahmp_snow

 use netcdf

 use NoahMPdisag_module, only : noahmp_type, UpdateAllLayers

 implicit none

 include 'mpif.h'

 type(noahmp_type)      :: noahmp_state

 integer :: res, len_land_vec 
 character(len=8) :: date_str 
 character(len=2) :: hour_str
 character(len=3) :: frac_grid

 ! index to map between tile and vector space 
 integer, allocatable :: tile2vector(:,:) 
 double precision, allocatable :: increment(:) 
 double precision, allocatable :: swe_back(:) 
 double precision, allocatable :: snow_depth_back(:) 

 integer :: ierr, nprocs, myrank, lunit, ncid, n
 logical :: file_exists

 ! restart variables that apply to full grid cell 
 ! (cf those that are land only)
 type grid_type
     double precision, allocatable :: land_frac          (:)
     double precision, allocatable :: swe                (:)
     double precision, allocatable :: snow_depth         (:)
     character(len=10)  :: name_snow_depth
     character(len=10)  :: name_swe
 endtype 
 type(grid_type) :: grid_state

 character*100      :: orog_path
 character*20       :: otype ! orography filename stub. For atm only, oro_C${RES}, for atm/ocean oro_C${RES}.mx100

 namelist /noahmp_snow/ date_str, hour_str, res, frac_grid, orog_path, otype
!
    call mpi_init(ierr)
    call mpi_comm_size(mpi_comm_world, nprocs, ierr)
    call mpi_comm_rank(mpi_comm_world, myrank, ierr)

    print*
    print*,"starting apply_incr_noahmp_snow program on rank ", myrank

    ! READ NAMELIST 

    inquire (file='apply_incr_nml', exist=file_exists) 

    if (.not. file_exists) then
        write (6, *) 'ERROR: apply_incr_nml does not exist'
        call mpi_abort(mpi_comm_world, 10)
    end if

    open (action='read', file='apply_incr_nml', iostat=ierr, newunit=lunit)
    read (nml=noahmp_snow, iostat=ierr, unit=lunit)

    ! SET VARIABLE NAMES FOR SNOW OVER LAND AND GRID
    if (frac_grid=="YES") then 
        noahmp_state%name_snow_depth =  'snodl     '
        noahmp_state%name_swe =         'weasdl    '
        grid_state%name_snow_depth =    'snwdph    '
        grid_state%name_swe =           'sheleg    '
    else
        noahmp_state%name_snow_depth =  'snwdph    '
        noahmp_state%name_swe =         'sheleg    '
        grid_state%name_snow_depth =    'snwdph    '
        grid_state%name_swe =           'sheleg    '
    endif


    ! GET MAPPING INDEX (see subroutine comments re: source of land/sea mask)

    call get_fv3_mapping(myrank, date_str, hour_str, res, len_land_vec, frac_grid, tile2vector)
  
    ! SET-UP THE NOAH-MP STATE  AND INCREMENT

    allocate(noahmp_state%swe                (len_land_vec)) ! values over land only
    allocate(noahmp_state%snow_depth         (len_land_vec)) ! values over land only 
    allocate(noahmp_state%active_snow_layers (len_land_vec)) 
    allocate(noahmp_state%swe_previous       (len_land_vec))
    allocate(noahmp_state%snow_soil_interface(len_land_vec,7))
    allocate(noahmp_state%temperature_snow   (len_land_vec,3))
    allocate(noahmp_state%snow_ice_layer     (len_land_vec,3))
    allocate(noahmp_state%snow_liq_layer     (len_land_vec,3))
    allocate(noahmp_state%temperature_soil   (len_land_vec))
    allocate(increment   (len_land_vec)) ! increment to snow depth over land

    if (frac_grid=="YES") then
        allocate(grid_state%land_frac          (len_land_vec)) 
        allocate(grid_state%swe                (len_land_vec)) ! values over full grid
        allocate(grid_state%snow_depth         (len_land_vec)) ! values over full grid
        allocate(swe_back                      (len_land_vec)) ! save background 
        allocate(snow_depth_back               (len_land_vec)) !
    endif

    ! READ RESTART FILE 

    call   read_fv3_restart(myrank, date_str, hour_str, res, ncid, & 
                len_land_vec, tile2vector, frac_grid, noahmp_state, grid_state)

    ! READ SNOW DEPTH INCREMENT

    call   read_fv3_increment(myrank, date_str, hour_str, res, &
                len_land_vec, tile2vector, noahmp_state%name_snow_depth, increment)
 
    if (frac_grid=="YES") then ! save background
        swe_back = noahmp_state%swe
        snow_depth_back = noahmp_state%snow_depth
    endif 

    ! ADJUST THE SNOW STATES OVER LAND

    call UpdateAllLayers(len_land_vec, increment, noahmp_state)

    ! IF FRAC GRID, ADJUST SNOW STATES OVER GRID CELL

    if (frac_grid=="YES") then

        ! get the land frac 
         call  read_fv3_orog(myrank, res, orog_path, otype, len_land_vec, tile2vector, & 
                grid_state)

         do n=1,len_land_vec 
                grid_state%swe(n) = grid_state%swe(n) + & 
                                grid_state%land_frac(n)* ( noahmp_state%swe(n) - swe_back(n)) 
                grid_state%snow_depth(n) = grid_state%snow_depth(n) + & 
                                grid_state%land_frac(n)* ( noahmp_state%snow_depth(n) - snow_depth_back(n)) 
         enddo


    endif

    ! WRITE OUT ADJUSTED RESTART

    call   write_fv3_restart(noahmp_state, grid_state, res, ncid, len_land_vec, & 
                frac_grid, tile2vector) 


    ! CLOSE RESTART FILE 
    print*
    print*,"closing restart, apply_incr_noahmp_snow program on rank ", myrank
    ierr = nf90_close(ncid)

    call mpi_finalize(ierr)

 contains 

!--------------------------------------------------------------
! if at netcdf call returns an error, print out a message
! and stop processing.
!--------------------------------------------------------------
 subroutine netcdf_err( err, string )

        implicit none

        include 'mpif.h'

        integer, intent(in) :: err
        character(len=*), intent(in) :: string
        character(len=80) :: errmsg

        if( err == nf90_noerr )return
        errmsg = nf90_strerror(err)
        print*,''
        print*,'fatal error: ', trim(string), ': ', trim(errmsg)
        print*,'stop.'
        call mpi_abort(mpi_comm_world, 999)

        return
 end subroutine netcdf_err


!--------------------------------------------------------------
! Get land sea mask from fv3 restart, and use to create 
! index for mapping from tiles (FV3 UFS restart) to vector
!  of land locations (offline Noah-MP restart)
! NOTE: slmsk in the restarts counts grid cells as land if 
!       they have a non-zero land fraction. Excludes grid 
!       cells that are surrounded by sea (islands). The slmsk 
!       in the oro_grid files (used by JEDI for screening out 
!       obs is different, and counts grid cells as land if they 
!       are more than 50% land (same exclusion of islands). If 
!       we want to change these definitations, may need to use 
!       land_frac field from the oro_grid files.
!--------------------------------------------------------------

 subroutine get_fv3_mapping(myrank, date_str, hour_str, res, & 
                len_land_vec, frac_grid, tile2vector)

 implicit none 

 include 'mpif.h'

 integer, intent(in) :: myrank, res
 character(len=8), intent(in) :: date_str 
 character(len=2), intent(in) :: hour_str 
 character(len=3), intent(in) :: frac_grid
 integer, allocatable, intent(out) :: tile2vector(:,:)
 integer :: len_land_vec

 character(len=100) :: restart_file
 character(len=1) :: rankch
 logical :: file_exists
 integer :: ierr,  ncid
 integer :: id_dim, id_var, fres
 integer :: slmsk(res,res) ! saved as double in the file, but i think this is OK
 integer :: vtype(res,res) ! saved as double in the file, but i think this is OK
 integer, parameter :: vtype_landice=15
 double precision :: fice(res,res)
 double precision, parameter :: fice_fhold = 0.00001
 integer :: i, j, nn

    ! OPEN FILE
    write(rankch, '(i1.1)') (myrank+1)
    restart_file = date_str//"."//hour_str//"0000.sfc_data.tile"//rankch//".nc"

    inquire(file=trim(restart_file), exist=file_exists)

    if (.not. file_exists) then
            print *, 'restart_file does not exist, ', &
                    trim(restart_file) , ' exiting'
            call mpi_abort(mpi_comm_world, 10) 
    endif

    write (6, *) 'calculate mapping from land mask in ', trim(restart_file)

    ierr=nf90_open(trim(restart_file),nf90_write,ncid)
    call netcdf_err(ierr, 'opening file: '//trim(restart_file) )

    ! READ MASK 
    ierr=nf90_inq_varid(ncid, "slmsk", id_var)
    call netcdf_err(ierr, 'reading slmsk id' )
    ierr=nf90_get_var(ncid, id_var, slmsk)
    call netcdf_err(ierr, 'reading slmsk' )
 
    ! REMOVE GLACIER GRID POINTS
    ierr=nf90_inq_varid(ncid, "vtype", id_var)
    call netcdf_err(ierr, 'reading vtype id' )
    ierr=nf90_get_var(ncid, id_var, vtype)
    call netcdf_err(ierr, 'reading vtype' )

    ! remove land grid cells if glacier land type
    do i = 1, res 
        do j = 1, res  
            if ( vtype(i,j) ==  vtype_landice)  slmsk(i,j)=0 ! vtype is integer, but stored as double
        enddo 
    enddo
 
    if (frac_grid=="YES") then 

        write (6, *) 'fractional grid: ammending mask to exclude sea ice from', trim(restart_file)

        ierr=nf90_inq_varid(ncid, "fice", id_var)
        call netcdf_err(ierr, 'reading fice id' )
        ierr=nf90_get_var(ncid, id_var, fice)
        call netcdf_err(ierr, 'reading fice' )

        ! remove land grid cells if ice is present
        do i = 1, res 
            do j = 1, res  
                if (fice(i,j) > fice_fhold ) slmsk(i,j)=0
            enddo 
        enddo


    endif
 
    ! get number of land points
    len_land_vec = 0
    do i = 1, res 
        do j = 1, res 
             if ( slmsk(i,j) == 1)  len_land_vec = len_land_vec+ 1  
        enddo 
    enddo
    
    write(6,*) 'Number of land points on rank ', myrank, ' :',  len_land_vec

    allocate(tile2vector(len_land_vec,2)) 

    nn=0
    do i = 1, res 
        do j = 1, res 
             if ( slmsk(i,j) == 1)   then 
                nn=nn+1
                tile2vector(nn,1) = i 
                tile2vector(nn,2) = j 
             endif
        enddo 
    enddo

end subroutine get_fv3_mapping


!--------------------------------------------------------------
! open fv3 restart, and read in required variables
! file is opened as read/write and remains open
!--------------------------------------------------------------
 subroutine read_fv3_restart(myrank, date_str, hour_str, res, ncid, & 
                len_land_vec,tile2vector, frac_grid, noahmp_state, grid_state)

 implicit none 

 include 'mpif.h'

 integer, intent(in) :: myrank, res, len_land_vec
 character(len=8), intent(in) :: date_str 
 character(len=2), intent(in) :: hour_str 
 integer, intent(in) :: tile2vector(len_land_vec,2)
 character(len=3), intent(in) :: frac_grid

 integer, intent(out) :: ncid
 type(noahmp_type), intent(inout)  :: noahmp_state
 type(grid_type), intent(inout)  :: grid_state

 character(len=100) :: restart_file
 character(len=1) :: rankch
 logical :: file_exists
 integer :: ierr, id_dim, fres
 integer :: nn

    ! OPEN FILE
    write(rankch, '(i1.1)') (myrank+1)
    restart_file = date_str//"."//hour_str//"0000.sfc_data.tile"//rankch//".nc"

    inquire(file=trim(restart_file), exist=file_exists)

    if (.not. file_exists) then
            print *, 'restart_file does not exist, ', &
                    trim(restart_file) , ' exiting'
            call mpi_abort(mpi_comm_world, 10) 
    endif

    write (6, *) 'opening ', trim(restart_file)

    ierr=nf90_open(trim(restart_file),nf90_write,ncid)
    call netcdf_err(ierr, 'opening file: '//trim(restart_file) )

    ! CHECK DIMENSIONS
    ierr=nf90_inq_dimid(ncid, 'xaxis_1', id_dim)
    call netcdf_err(ierr, 'reading xaxis_1' )
    ierr=nf90_inquire_dimension(ncid,id_dim,len=fres)
    call netcdf_err(ierr, 'reading xaxis_1' )

    if ( fres /= res) then
       print*,'fatal error: dimensions wrong.'
       call mpi_abort(mpi_comm_world, ierr)
    endif

   ! read swe over land (file name: sheleg, vert dim 1) 
    call read_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                        noahmp_state%name_swe, noahmp_state%swe)

    ! read snow_depth over land (file name: snwdph, vert dim 1)
    call read_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                        noahmp_state%name_snow_depth, noahmp_state%snow_depth)

   if (frac_grid=="YES") then 
       ! read swe over grid cell  (file name: sheleg, vert dim 1) 
        call read_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                            grid_state%name_swe, grid_state%swe)

        ! read snow_depth  over grid cell (file name: snwdph, vert dim 1)
        call read_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                            grid_state%name_snow_depth, grid_state%snow_depth)
    endif

    ! read active_snow_layers (file name: snowxy, vert dim: 1) 
    call read_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                        'snowxy    ', noahmp_state%active_snow_layers)

    ! read swe_previous (file name: sneqvoxy, vert dim: 1) 
    call read_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                        'sneqvoxy  ', noahmp_state%swe_previous)

    ! read snow_soil_interface (file name: zsnsoxy, vert dim: 7) 
    call read_nc_var3D(ncid, len_land_vec, res, 7,  tile2vector, & 
                        'zsnsoxy   ', noahmp_state%snow_soil_interface)

    ! read temperature_snow (file name: tsnoxy, vert dim: 3) 
    call read_nc_var3D(ncid, len_land_vec, res, 3, tile2vector, & 
                        'tsnoxy    ', noahmp_state%temperature_snow)

    ! read snow_ice_layer (file name:  snicexy, vert dim: 3) 
    call read_nc_var3D(ncid, len_land_vec, res, 3, tile2vector, & 
                        'snicexy    ', noahmp_state%snow_ice_layer)

    ! read snow_liq_layer (file name: snliqxy, vert dim: 3) 
    call read_nc_var3D(ncid, len_land_vec, res, 3, tile2vector, & 
                        'snliqxy   ', noahmp_state%snow_liq_layer)

    ! read temperature_soil (file name: stc, use layer 1 only, vert dim: 1) 
    call read_nc_var2D(ncid, len_land_vec, res, tile2vector, 4, & 
                        'stc       ', noahmp_state%temperature_soil)

end subroutine read_fv3_restart


!--------------------------------------------------------------
! open fv3 orography file, and read in land fraction
!--------------------------------------------------------------
 subroutine read_fv3_orog(myrank, res, orog_path, otype, len_land_vec, tile2vector, & 
                grid_state)

 implicit none 

 include 'mpif.h'

 integer, intent(in) :: myrank, res, len_land_vec
 character(len=100), intent(in)  :: orog_path
 character(len=20), intent(in)   :: otype
 integer, intent(in) :: tile2vector(len_land_vec,2)
 type(grid_type), intent(inout) :: grid_state

 character(len=250) :: filename
 character(len=1) :: rankch
 logical :: file_exists
 integer :: ncid, id_dim, id_var, ierr, fres

    ! OPEN FILE
    write(rankch, '(i1.1)') (myrank+1)
    filename =trim(orog_path)//"/"//trim(otype)//".tile"//rankch//".nc"

    inquire(file=trim(filename), exist=file_exists)

    if (.not. file_exists) then
            print *, 'filename does not exist, ', &
                    trim(filename) , ' exiting'
            call mpi_abort(mpi_comm_world, 10) 
    endif

    write (6, *) 'opening ', trim(filename)

    ierr=nf90_open(trim(filename),nf90_nowrite,ncid)
    call netcdf_err(ierr, 'opening file: '//trim(filename) )

    ! CHECK DIMENSIONS
    ierr=nf90_inq_dimid(ncid, 'lon', id_dim)
    call netcdf_err(ierr, 'reading lon' )
    ierr=nf90_inquire_dimension(ncid,id_dim,len=fres)
    call netcdf_err(ierr, 'reading lon' )

    if ( fres /= res) then
       print*,'fatal error: dimensions wrong.'
       call mpi_abort(mpi_comm_world, ierr)
    endif

   ! read swe over grid cell  (file name: sheleg, vert dim 1) 
    call read_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                        'land_frac  ', grid_state%land_frac)

    ! close file 
    write (6, *) 'closing ', trim(filename)

    ierr=nf90_close(ncid)
    call netcdf_err(ierr, 'closing file: '//trim(filename) )

end subroutine read_fv3_orog

!--------------------------------------------------------------
!  read in snow depth increment from jedi increment file
!  file format is same as restart file
!--------------------------------------------------------------
 subroutine read_fv3_increment(myrank, date_str, hour_str, res, & 
                len_land_vec,tile2vector, control_var, increment)

 implicit none 

 include 'mpif.h'

 integer, intent(in) :: myrank, res, len_land_vec
 character(len=8), intent(in) :: date_str 
 character(len=2), intent(in) :: hour_str 
 integer, intent(in) :: tile2vector(len_land_vec,2)
 character(len=10), intent(in)  :: control_var
 double precision, intent(out) :: increment(len_land_vec)     ! snow depth increment

 character(len=100) :: incr_file
 character(len=1) :: rankch
 logical :: file_exists
 integer :: ierr 
 integer :: id_dim, id_var, fres, ncid
 integer :: nn


 
    ! OPEN FILE
    write(rankch, '(i1.1)') (myrank+1)
    incr_file = date_str//"."//hour_str//"0000.xainc.sfc_data.tile"//rankch//".nc"

    inquire(file=trim(incr_file), exist=file_exists)

    if (.not. file_exists) then
            print *, 'incr_file does not exist, ', &
                    trim(incr_file) , ' exiting'
            call mpi_abort(mpi_comm_world, 10) 
    endif

    write (6, *) 'opening ', trim(incr_file)

    ierr=nf90_open(trim(incr_file),nf90_nowrite,ncid)
    call netcdf_err(ierr, 'opening file: '//trim(incr_file) )

    ! CHECK DIMENSIONS
    ierr=nf90_inq_dimid(ncid, 'xaxis_1', id_dim)
    call netcdf_err(ierr, 'reading xaxis_1' )
    ierr=nf90_inquire_dimension(ncid,id_dim,len=fres)
    call netcdf_err(ierr, 'reading xaxis_1' )

    if ( fres /= res) then
       print*,'fatal error: dimensions wrong.'
       call mpi_abort(mpi_comm_world, ierr)
    endif

    ! read snow_depth (file name: snwdph, vert dim 1)
    call read_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                        control_var, increment)

    ! close file 
    write (6, *) 'closing ', trim(incr_file)

    ierr=nf90_close(ncid)
    call netcdf_err(ierr, 'closing file: '//trim(incr_file) )

end subroutine  read_fv3_increment

!--------------------------------------------------------
! Subroutine to read in a 2D variable from netcdf file, 
! and save to noahmp vector
!--------------------------------------------------------

subroutine read_nc_var2D(ncid, len_land_vec, res, tile2vector, in3D_vdim,  & 
                         var_name, data_vec)

    integer, intent(in)             :: ncid, len_land_vec, res 
    character(len=10), intent(in)   :: var_name
    integer, intent(in)             :: tile2vector(len_land_vec,2)
    integer, intent(in)             :: in3D_vdim ! 0 - input is 2D, 
                                                 ! >0, gives dim of 3rd dimension
    double precision, intent(out)   :: data_vec(len_land_vec) 

    double precision :: dummy2D(res, res) 
    double precision :: dummy3D(res, res, in3D_vdim)  
    integer          :: nn, ierr, id_var

    ierr=nf90_inq_varid(ncid, trim(var_name), id_var)
    call netcdf_err(ierr, 'reading '//var_name//' id' )
    if (in3D_vdim==0) then
        ierr=nf90_get_var(ncid, id_var, dummy2D)
        call netcdf_err(ierr, 'reading '//var_name//' data' )
    else  ! special case for reading in 3D variable, and retaining only 
          ! level 1
        ierr=nf90_get_var(ncid, id_var, dummy3D)
        call netcdf_err(ierr, 'reading '//var_name//' data' )
        dummy2D=dummy3D(:,:,1) 
    endif

    do nn=1,len_land_vec 
        data_vec(nn) = dummy2D(tile2vector(nn,1), tile2vector(nn,2))
    enddo

end subroutine read_nc_var2D

!--------------------------------------------------------
! Subroutine to read in a 3D variable from netcdf file, 
! and save to noahmp vector
!--------------------------------------------------------

subroutine read_nc_var3D(ncid, len_land_vec, res, vdim,  & 
                tile2vector, var_name, data_vec)

    integer, intent(in)             :: ncid, len_land_vec, res, vdim
    character(len=10), intent(in)   :: var_name
    integer, intent(in)             :: tile2vector(len_land_vec,2)
    double precision, intent(out)   :: data_vec(len_land_vec, vdim)

    double precision :: dummy3D(res, res, vdim) 
    integer          :: nn, ierr, id_var

    ierr=nf90_inq_varid(ncid, trim(var_name), id_var)
    call netcdf_err(ierr, 'reading '//var_name//' id' )
    ierr=nf90_get_var(ncid, id_var, dummy3D)
    call netcdf_err(ierr, 'reading '//var_name//' data' )

    do nn=1,len_land_vec 
        data_vec(nn,:) = dummy3D(tile2vector(nn,1), tile2vector(nn,2), :) 
    enddo

end subroutine read_nc_var3D

!--------------------------------------------------------------
! write updated fields tofv3_restarts  open on ncid
!--------------------------------------------------------------
 subroutine write_fv3_restart(noahmp_state, grid_state, res, ncid, len_land_vec, &
                 frac_grid, tile2vector) 

 implicit none 

 integer, intent(in) :: ncid, res, len_land_vec
 type(noahmp_type), intent(in) :: noahmp_state
 type(grid_type), intent(in) :: grid_state
 character(len=3), intent(in) :: frac_grid
 integer, intent(in) :: tile2vector(len_land_vec,2)

 
   ! write swe over land (file name: sheleg, vert dim 1) 
    call write_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                        noahmp_state%name_swe, noahmp_state%swe)

    ! write snow_depth over land (file name: snwdph, vert dim 1)
    call write_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                        noahmp_state%name_snow_depth, noahmp_state%snow_depth)

    if (frac_grid=="YES") then
       ! write swe over grid (file name: sheleg, vert dim 1) 
        call write_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                            grid_state%name_swe, grid_state%swe)

        ! write snow_depth over grid (file name: snwdph, vert dim 1)
        call write_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                            grid_state%name_snow_depth, grid_state%snow_depth)
    endif 

    ! write active_snow_layers (file name: snowxy, vert dim: 1) 
    call write_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                        'snowxy    ', noahmp_state%active_snow_layers)

    ! write swe_previous (file name: sneqvoxy, vert dim: 1) 
    call write_nc_var2D(ncid, len_land_vec, res, tile2vector, 0, & 
                        'sneqvoxy  ', noahmp_state%swe_previous)

    ! write snow_soil_interface (file name: zsnsoxy, vert dim: 7) 
    call write_nc_var3D(ncid, len_land_vec, res, 7,  tile2vector, & 
                        'zsnsoxy   ', noahmp_state%snow_soil_interface)

    ! write temperature_snow (file name: tsnoxy, vert dim: 3) 
    call write_nc_var3D(ncid, len_land_vec, res, 3, tile2vector, & 
                        'tsnoxy    ', noahmp_state%temperature_snow)

    ! write snow_ice_layer (file name:  snicexy, vert dim: 3) 
    call write_nc_var3D(ncid, len_land_vec, res, 3, tile2vector, & 
                        'snicexy    ', noahmp_state%snow_ice_layer)

    ! write snow_liq_layer (file name: snliqxy, vert dim: 3) 
    call write_nc_var3D(ncid, len_land_vec, res, 3, tile2vector, & 
                        'snliqxy   ', noahmp_state%snow_liq_layer)

    ! write temperature_soil (file name: stc, use layer 1 only, vert dim: 1) 
    call write_nc_var2D(ncid, len_land_vec, res, tile2vector, 4, & 
                        'stc       ', noahmp_state%temperature_soil)


 end subroutine write_fv3_restart


!--------------------------------------------------------
! Subroutine to write a 2D variable to the netcdf file 
!--------------------------------------------------------

subroutine write_nc_var2D(ncid, len_land_vec, res, tile2vector,   & 
                in3D_vdim, var_name, data_vec)

    integer, intent(in)             :: ncid, len_land_vec, res
    character(len=10), intent(in)   :: var_name
    integer, intent(in)             :: tile2vector(len_land_vec,2)
    integer, intent(in)             :: in3D_vdim ! 0 - input is 2D, 
                                                 ! >0, gives dim of 3rd dimension
    double precision, intent(in)    :: data_vec(len_land_vec)

    double precision :: dummy2D(res, res) 
    double precision :: dummy3D(res, res, in3D_vdim)
    integer          :: nn, ierr, id_var

    ierr=nf90_inq_varid(ncid, trim(var_name), id_var)
    call netcdf_err(ierr, 'reading '//trim(var_name)//' id' )
    if (in3D_vdim==0) then 
        ierr=nf90_get_var(ncid, id_var, dummy2D)
        call netcdf_err(ierr, 'reading '//trim(var_name)//' data' )
    else  ! special case for reading in multi-level variable, and 
          ! retaining only first level.
        ierr=nf90_get_var(ncid, id_var, dummy3D)
        call netcdf_err(ierr, 'reading '//trim(var_name)//' data' )
        dummy2D = dummy3D(:,:,1)
    endif
    
    ! sub in updated locations (retain previous fields for non-land)  
    do nn=1,len_land_vec 
        dummy2D(tile2vector(nn,1), tile2vector(nn,2)) = data_vec(nn) 
    enddo

    ! overwrite
    if (in3D_vdim==0) then 
        ierr = nf90_put_var( ncid, id_var, dummy2D)
        call netcdf_err(ierr, 'writing '//trim(var_name) )
    else 
        dummy3D(:,:,1) = dummy2D 
        ierr = nf90_put_var( ncid, id_var, dummy3D)
        call netcdf_err(ierr, 'writing '//trim(var_name) )
    endif
 
end subroutine write_nc_var2D

!--------------------------------------------------------
! Subroutine to write a 3D variable to the netcdf file 
!--------------------------------------------------------

subroutine write_nc_var3D(ncid, len_land_vec, res, vdim, & 
                tile2vector, var_name, data_vec)

    integer, intent(in)             :: ncid, len_land_vec, res, vdim
    character(len=10), intent(in)   :: var_name
    integer, intent(in)             :: tile2vector(len_land_vec,2)
    double precision, intent(in)    :: data_vec(len_land_vec, vdim)

    double precision :: dummy3D(res, res, vdim)
    integer          :: nn, ierr, id_var

    ierr=nf90_inq_varid(ncid, trim(var_name), id_var)
    call netcdf_err(ierr, 'reading '//trim(var_name)//' id' )
    ierr=nf90_get_var(ncid, id_var, dummy3D)
    call netcdf_err(ierr, 'reading '//trim(var_name)//' data' )
    
    ! sub in updated locations (retain previous fields for non-land)  
    do nn=1,len_land_vec 
        dummy3D(tile2vector(nn,1), tile2vector(nn,2),:) = data_vec(nn,:)
    enddo

    ! overwrite
    ierr = nf90_put_var( ncid, id_var, dummy3D)
    call netcdf_err(ierr, 'writing '//trim(var_name) )
 
end subroutine write_nc_var3D

 end program apply_incr_noahmp_snow
