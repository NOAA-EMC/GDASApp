module NoahMPdisag_module

  private

  public noahmp_type
  public UpdateAllLayers

! Note: in GFS with fractional grid cells, the swe and snow_depth saved in noahmp_type are the 
!       values over the land fraction only. The restarts have a separate variable with the grid 
!       cell average. All other varibales here (except temperature_soil) are Noah-MP specific, 
!       and are defined only over land.

  type noahmp_type
    double precision, allocatable :: swe                (:)
    double precision, allocatable :: snow_depth         (:)
    double precision, allocatable :: active_snow_layers (:)
    double precision, allocatable :: swe_previous       (:)
    double precision, allocatable :: snow_soil_interface(:,:)
    double precision, allocatable :: temperature_snow   (:,:)
    double precision, allocatable :: snow_ice_layer     (:,:)
    double precision, allocatable :: snow_liq_layer     (:,:)
    double precision, allocatable :: temperature_soil   (:)
    character(len=10)      :: name_snow_depth
    character(len=10)      :: name_swe
  end type noahmp_type    

contains   

  subroutine UpdateAllLayers(vector_length, increment, noahmp)

 ! intent(in)  
  integer, intent(in)                :: vector_length
  double precision, intent(in)       :: increment(vector_length) ! snow depth increment

! intent(inout)
  type(noahmp_type), intent(inout)   :: noahmp

  double precision       :: layer_density, swe_increment, liq_ratio 
  integer                :: iloc, ilayer, iinter, active_layers, vector_loc, pathway 
  double precision       :: soil_interfaces(7) = (/0.0,0.0,0.0,0.1,0.4,1.0,2.0/)
  double precision       :: partition_ratio, layer_depths(3), anal_snow_depth
  double precision       :: temp_soil_corr
  integer                :: count0, count1, count2, count3, count4, count5, count6, count7
  
  associate( &
                 swe => noahmp%swe                ,&
          snow_depth => noahmp%snow_depth         ,&
  active_snow_layers => noahmp%active_snow_layers ,&
        swe_previous => noahmp%swe_previous       ,&
 snow_soil_interface => noahmp%snow_soil_interface,&
    temperature_snow => noahmp%temperature_snow   ,&
      snow_ice_layer => noahmp%snow_ice_layer     ,&
      snow_liq_layer => noahmp%snow_liq_layer     ,&
    temperature_soil => noahmp%temperature_soil )

  count0=0
  count1=0
  count2=0
  count3=0
  count4=0
  count5=0
  count6=0
  count7=0
  
  do iloc = 1, vector_length
    temp_soil_corr = min(273.15, temperature_soil(iloc))
    
    pathway = -1  !  increment is zero.

    anal_snow_depth = snow_depth(iloc) + increment(iloc) ! analysed bulk snow depth

    if (abs( increment(iloc)) > 0.01 )  then ! skip if no (or small) increment 
        
        if(anal_snow_depth <=  0.0001) then ! correct negative snow depth here

          pathway = 0  !  analysis is zero (or negative) 
          count1 = count1+1

          swe                (iloc)   = 0.0
          snow_depth         (iloc)   = 0.0
          active_snow_layers (iloc)   = 0.0
          swe_previous       (iloc)   = 0.0
          snow_soil_interface(iloc,:) = (/0.0,0.0,0.0,-0.1,-0.4,-1.0,-2.0/)
          temperature_snow   (iloc,:) = 0.0
          snow_ice_layer     (iloc,:) = 0.0
          snow_liq_layer     (iloc,:) = 0.0

        else
        
          active_layers = nint(active_snow_layers(iloc))  ! number of active layers (0,-1,-2,-3)

          if(active_layers < 0) then  ! in multi-layer mode
          
            layer_depths(1) = snow_soil_interface(iloc,1)
            layer_depths(2) = snow_soil_interface(iloc,2)-snow_soil_interface(iloc,1)
            layer_depths(3) = snow_soil_interface(iloc,3)-snow_soil_interface(iloc,2)

            if(increment(iloc) > 0.0) then  ! add snow in multi-layer mode

              pathway = 1 ! adding snow in multi-layer mode
              count2 = count2+1
        
              vector_loc = 4 + active_layers  ! location in vector of top layer
              
              layerloop: do ilayer = vector_loc, 3
              
                partition_ratio = -layer_depths(ilayer)/snow_depth(iloc)*1000.d0
                layer_density = (snow_ice_layer(iloc,ilayer)+snow_liq_layer(iloc,ilayer)) / &
                                  (-layer_depths(ilayer))
                swe_increment = partition_ratio * increment(iloc) * layer_density / 1000.d0
                !liq_ratio = snow_liq_layer(iloc,ilayer) / &
                !              ( snow_ice_layer(iloc,ilayer) + snow_liq_layer(iloc,ilayer) )
                liq_ratio = 0. ! add all new snow as ice.
                snow_ice_layer(iloc,ilayer) = snow_ice_layer(iloc,ilayer) + &
                                                  (1.0 - liq_ratio) * swe_increment
                snow_liq_layer(iloc,ilayer) = snow_liq_layer(iloc,ilayer) + &
                                                  liq_ratio * swe_increment
                do iinter = ilayer, 3  ! remove snow from each snow layer
                  snow_soil_interface(iloc,iinter) = snow_soil_interface(iloc,iinter) - &
                                                       partition_ratio * increment(iloc)/1000.d0
                end do

              end do layerloop
                
            elseif(increment(iloc) < 0.0) then  ! remove snow in multi-layer mode

              pathway = 2 ! removing snow in multi-layer mode 
              count3 = count3+1
              
              vector_loc = 4 + active_layers  ! location in vector of top layer
              
              layerloop: do ilayer = vector_loc, 3
              
                partition_ratio = -layer_depths(ilayer)/snow_depth(iloc)*1000.d0
                layer_density = (snow_ice_layer(iloc,ilayer)+snow_liq_layer(iloc,ilayer)) / &
                                  (-layer_depths(ilayer))
                swe_increment = partition_ratio * increment(iloc) * layer_density / 1000.d0
                liq_ratio = snow_liq_layer(iloc,ilayer) / &
                              ( snow_ice_layer(iloc,ilayer) + snow_liq_layer(iloc,ilayer) )
                snow_ice_layer(iloc,ilayer) = snow_ice_layer(iloc,ilayer) + &
                                                  (1.0 - liq_ratio) * swe_increment
                snow_liq_layer(iloc,ilayer) = snow_liq_layer(iloc,ilayer) + &
                                                  liq_ratio * swe_increment
                do iinter = ilayer, 3  ! remove snow from each snow layer
                  snow_soil_interface(iloc,iinter) = snow_soil_interface(iloc,iinter) - &
                                                       partition_ratio * increment(iloc)/1000.d0
                end do

              end do layerloop
              
            end if  ! increment
            
            ! For multi-layer mode, recalculate interfaces and sum depth/swe

            do ilayer = 4, 7
              snow_soil_interface(iloc,ilayer) = snow_soil_interface(iloc,3) - soil_interfaces(ilayer)
            end do

            snow_depth(iloc) = -snow_soil_interface(iloc,3) * 1000.d0

            swe(iloc) = 0.0

            do ilayer = 1, 3
              swe(iloc) = swe(iloc) + snow_ice_layer(iloc,ilayer) + snow_liq_layer(iloc,ilayer)
            end do

            swe_previous(iloc) = swe(iloc)

            if(snow_depth(iloc) < 25.d0) then  ! go out of multi-layer mode
              active_snow_layers (iloc) = 0.d0
              snow_soil_interface(iloc,:) = (/0.0,0.0,0.0,-0.1,-0.4,-1.0,-2.0/)
              temperature_snow   (iloc,:) = 0.0
              snow_ice_layer     (iloc,:) = 0.0
              snow_liq_layer     (iloc,:) = 0.0
            end if

          elseif(active_layers == 0) then  ! snow starts in zero-layer mode

            if(increment(iloc) > 0.0) then  ! add snow in zero-layer mode

              !if(snow_depth(iloc) == 0) then   ! no snow present, so assume density based on soil temperature
              if(snow_depth(iloc) < 1.) then   ! need at least 1 mm, or use new snow density
                pathway = 3 ! adding snow in zero-layer mode, no snow present
                layer_density = max(80.0,min(120.,67.92+51.25*exp((temp_soil_corr-273.15)/2.59)))
              else   ! use existing density
                pathway = 4 ! adding snow in zero-layer mode, snow present
                layer_density = swe(iloc) / snow_depth(iloc) * 1000.d0
              end if
              if (temperature_soil(iloc)<=273.155) then  ! do not add is soil too warm (will melt)
                  snow_depth(iloc) = min(snow_depth(iloc) + increment(iloc), 50.) ! limit amount of snow that can 
                                                                                  ! be added so that no more than one layer 
                                                                                  ! is created.
                  swe(iloc) = swe(iloc) + increment(iloc) * layer_density / 1000.d0
                  count4 = count4+1
              else 
                  count5 = count5+1
              endif
              swe_previous(iloc) = swe(iloc)

              active_snow_layers(iloc)      = 0.0
              snow_ice_layer(iloc,:)        = 0.0
              snow_liq_layer(iloc,:)        = 0.0
              temperature_snow(iloc,:)      = 0.0
              snow_soil_interface(iloc,1:3) = 0.0

              if(snow_depth(iloc) > 25.0) then  ! snow depth is > 25mm so put in a layer
                pathway = 5 ! addition of snow caused creation of a layer
                count6 = count6+1
                active_snow_layers(iloc) = -1.0
                snow_ice_layer(iloc,3)   = swe(iloc)
                temperature_snow(iloc,3) = temp_soil_corr
                do ilayer = 3, 7
                  snow_soil_interface(iloc,ilayer) = snow_soil_interface(iloc,ilayer) - snow_depth(iloc)/1000.d0
                end do
              end if
              
            elseif(increment(iloc) < 0.0) then  ! remove snow in zero-layer mode

              pathway = 6 ! removing snow in zero layer mode
              count7=count7+1
        
              layer_density = swe(iloc) / snow_depth(iloc) * 1000.d0
              snow_depth(iloc) = snow_depth(iloc) + increment(iloc)
              swe(iloc) = swe(iloc) + increment(iloc) * layer_density / 1000.d0
              swe_previous(iloc) = swe(iloc)

              active_snow_layers(iloc)      = 0.0
              snow_ice_layer(iloc,:)        = 0.0
              snow_liq_layer(iloc,:)        = 0.0
              temperature_snow(iloc,:)      = 0.0
              snow_soil_interface(iloc,1:3) = 0.0

            end if  ! increment

          end if  ! active_layers
            
        end if  ! anal_snow_depth <= 0.
    else 
        count0 = count0+1 
    end if ! non-zero increment 
    ! do some gross checks

    if(abs(snow_soil_interface(iloc,7) - snow_soil_interface(iloc,3) + 2.d0) > 0.0000001) then
      print*, "Depth of soil not 2m"
      print*, pathway
      print*, snow_soil_interface(iloc,7), snow_soil_interface(iloc,3)
!      stop
    end if

    if(active_snow_layers(iloc) < 0.0 .and. abs(snow_depth(iloc) + 1000.d0*snow_soil_interface(iloc,3)) > 0.0000001) then
      print*, "snow_depth and snow_soil_interface inconsistent"
      print*, pathway
      print*, active_snow_layers(iloc), snow_depth(iloc), snow_soil_interface(iloc,3)
!      stop
    end if

    if( (abs(anal_snow_depth - snow_depth(iloc))   > 0.01) .and. (anal_snow_depth > 0.0001) .and. temperature_soil(iloc) <= 273.155 ) then
! this condition will fail if snow added was limitted to 50mm to avoid layering issues 
      print*, "snow increment and updated model snow inconsistent" 
      print*, pathway
      print*, anal_snow_depth, snow_depth(iloc), temperature_soil(iloc)
!      stop
    end if

    if(snow_depth(iloc) < 0.0 .or. snow_soil_interface(iloc,3) > 0.0 ) then
      print*, "snow depth or interface has wrong sign"
      print*, pathway
      print*, snow_depth(iloc), snow_soil_interface(iloc,3)
!      stop
    end if

  end do
 
  print *, "Noah-MP snow increment summary:" 
  print *, "No increments added: ", count0
  print *, "Increment removed all snow", count1 
  print *, "Increment added snow in multi-layer mode", count2
  print *, "Increment removed snow in multi-layer mode", count3
  print *, "Increment added snow in zero-layer mode", count4
  print *, "Increment not added in zero-layer mode, too warm", count5
  print *, "Increment added in zero-layer mode, added a layer", count6
  print *, "Increment removed snow in zero-layer mode", count7

  end associate
   
  end subroutine UpdateAllLayers
  
end module NoahMPdisag_module
