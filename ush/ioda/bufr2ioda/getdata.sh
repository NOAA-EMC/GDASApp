#!/bin/csh -xf
#===========================================================
# Plot statistics from two instrument together in one cycle
#===========================================================

#=======================
#  Get input parameters 
#=======================

set user    = Xin.C.Jin
set bdate   = 2021080100
set edate   = 2021080100
set cdate   = $bdate
set product = gdas

#   while ($cdate <= $edate) 

set yyyymmddhh=$cdate
set yyyymmdd=`echo $cdate | cut -c1-8`
set hh=`echo $cdate | cut -c9-10`

foreach inst (esamua 1bamua)

   set gdump     = /work/noaa/rstprod/dump/${product}.${yyyymmdd}/${hh}
   set bufrfile  = ${gdump}/gdas.t${hh}z.${inst}.tm00.bufr_d

   set work_dir = `pwd`
   set data_dir = ${work_dir}/testinput/${yyyymmddhh}

   if (!( -d $data_dir)) mkdir -p -m770 $data_dir

   ln -sf ${bufrfile} ${data_dir}

end

#      set cdate = `/home/Emily.Liu/bin/ndate +6 ${cdate}`

#   end

exit


