

### line 587 of sub2mem_mer.f

def sub2mem_mer(proflun, bmiss, mxlv, mxnmev, maxmandlvls, mandlvls, mesgtype, hdr2wrt,
                acid1, c_acftid1, c_acftreg1, rct_accum, drinfo_accum, acft_seq_accum,
                mstq_accum, cat_accum, elv_accum, rpt_accum, tcor_accum,
                pevn_accum, pbg_accum, ppp_accum, qevn_accum, qbg_accum, qpp_accum,
                tevn_accum, tbg_accum, tpp_accum, zevn_accum, zbg_accum, zpp_accum,
                wuvevn_accum, wuvbg_accum, wuvpp_accum, wdsevn_accum, mxe4prof,
                c_qc_accum, num_events_prof, lvlsinprof, nlvinprof, nrlacqc_pc,
                l_mandlvl, tsplines, l_operational, lwr):

    rate_accum = bmiss #NickE prob need to change to float missing
    if nlvinprof == 0:
        print('### PROBLEM - into subr, sub2mem_mer with nlvinprof = 0')
        print('              this should never happen')
# NickE
        call w3tage('PREPOBS_PREPACQC')
        call errexit(59)

# First sort pressures from lowest to highest, this will also determine the
# maximum and minimum pressure values in this profile

#NickE
    orders(1, iwork, lvlsinprof, iord, nlvinprof, 1, lwr, 2)

# Interpolate z,t,q,u,v values to mandatory levels
# include the levels of 1000, 850, 700, 500, 400, 300, 200, 150 and 100 mb
# in the acceptable mandatory levels for aircraft
# profiles (not many aircraft flying above 100 mb!)

    nmandlvls = 0
    nlv2wrt_tot = nlvinprof
    if l_mandlvl and nlvinprof > 1:
        for i in range(1, maxmandlvls + 1):
            for j in range(1, nlvinprof + 1):
# Below, jj points to level at a lower pressure/higher altitude and jjp1 points to the
#  adjacent level at a higher pressure, lower altitude)
                jj = iord[j]
                jjp1 = iord[j + 1]
                if j < nlvinprof:
                    if lvlsinprof[jj] < mandlvls[i] and lvlsinprof[jjp1] > mandlvls[i]:
                        if nlvinprof + nmandlvls + 1 > mxlv:
# There are more levels in profile than "mxlv" -- do not process any more levels
                            print(' #####> WARNING: THERE ARE MORE THAN ', mxlv, ' LEVELS IN THIS PROFILE -- WILL CONTINUE ON PROCESSING ONLY ', mxlv, ' LEVELS FOR THIS PROFILE')
                            cmxlv = str(mxlv)
                            break
                        nmandlvls = nmandlvls + 1
# Now calculate values on mandlvls(i) using values at lvlsinprof(j) (ll/lower level and (j+1)
# (ul/upper level) - USE REASON CODE 98 FOR INTERPOLATED MANDATORY LEVELS (use highest
# quality mark amongst lower and upper levels)
                        pll = lvlsinprof[jj]
                        pul = lvlsinprof[jjp1]
                        pqll = pevn_accum[2, jj, 1]
                        pqul = pevn_accum[2, jjp1, 1]
                        pml = mandlvls[i]
                        lvlsinprof[nlvinprof + nmandlvls] = mandlvls[i]
                        pevn_accum[1, nlvinprof + nmandlvls, 1] = pml / 10.
                        pevn_accum[2, nlvinprof + nmandlvls, 1] = max(pqll, pqul)
                        pevn_accum[3, nlvinprof + nmandlvls, 1] = nrlacqc_pc
                        pevn_accum[4, nlvinprof + nmandlvls, 1] = 98
                        cat_accum[1, nlvinprof + nmandlvls] = 7

# Temperature
                        if ibfms[tevn_accum[1, jj, 1]] == 0 and ibfms[tevn_accum[1, jjp1, 1]] == 0:
                            for iii in range(mxe4prof, 0, -1):
                                if ibfms[tevn_accum[1, jj, iii]] != 0:
                                    nevents_t = iii
                                else:
                                    nevents_t = iii
                                    break
                            tll = tevn_accum[1, jj, nevents_t]
                            tqll = tevn_accum[2, jj, nevents_t]
                            for iii in range(mxe4prof, 0, -1):
                                if ibfms[tevn_accum[1, jjp1, iii]] != 0:
                                    nevents_t = iii
                                else:
                                    nevents_t = iii
                                    break
                            tul = tevn_accum[1, jjp1, nevents_t]
                            tqul = tevn_accum[2, jjp1, nevents_t]
                            dt_dlnp = (tul - tll) / alog(pul / pll)
                            tml = tll + (dt_dlnp * (alog(pml / pll)))
                            tevn_accum[1, nlvinprof + nmandlvls, 1] = tml
                            tevn_accum[2, nlvinprof + nmandlvls, 1] = max(tqll, tqul)
                            tevn_accum[3, nlvinprof + nmandlvls, 1] = nrlacqc_pc
                            tevn_accum[4, nlvinprof + nmandlvls, 1] = 98

#Moisture
                        if ibfms[qevn_accum[1, jj, 1]] == 0 and ibfms[qevn_accum[1, jjp1, 1]] == 0:
                            for iii in range(mxe4prof, 0, -1):
                                if ibfms[qevn_accum[1, jj, iii]] != 0:
                                    nevents_q = iii
                                else:
                                    nevents_q = iii
                                    break
                            qll = qevn_accum[1, jj, nevents_q]
                            qqll = qevn_accum[2, jj, nevents_q]
                            for iii in range(mxe4prof, 0, -1):
                                if ibfms[qevn_accum[1, jjp1, iii]] != 0:
                                    nevents_q = iii
                                else:
                                    nevents_q = iii
                                    break
                            qul = qevn_accum[1, jjp1, nevents_q]
                            qqul = qevn_accum[2, jjp1, nevents_q]
                            dq_dlnp = (qul - qll) / alog(pul / pll)
                            qml = qll + (dq_dlnp * (alog(pml / pll)))
                            qevn_accum[1, nlvinprof + nmandlvls, 1] = qml
                            qevn_accum[2, nlvinprof + nmandlvls, 1] = max(qqll, qqul)
                            qevn_accum[3, nlvinprof + nmandlvls, 1] = nrlacqc_pc
                            qevn_accum[4, nlvinprof + nmandlvls, 1] = 98
                        else:
                            if ibfms[qbg_accum[2, jj]] == 0 and ibfms[qbg_accum[2, jjp1]] == 0:
                                qll = qbg_accum[2, jj]
                                qul = qbg_accum[2, jjp1]
                                dq_dlnp = (qul - qll) / alog(pul / pll)
                                qml = qll + (dq_dlnp * (alog(pml / pll)))
                                qbg_accum[2, nlvinprof + nmandlvls] = qml
# Altitude
                        if ibfms[zevn_accum[1, jj, 1]] == 0 and ibfms[zevn_accum[1, jjp1, 1]] == 0:
                            zll = zevn_accum[1, jj, 1]
                            zul = zevn_accum[1, jjp1, 1]
                            zqll = zevn_accum[2, jj, 1]
                            zqul = zevn_accum[2, jjp1, 1]
                            dz_dlnp = (zul - zll) / alog(pul / pll)
                            zml = zll + (dz_dlnp * (alog(pml / pll)))
                            zevn_accum[1, nlvinprof + nmandlvls, 1] = zml
                            zevn_accum[2, nlvinprof + nmandlvls, 1] = max(zqll, zqul)
                            zevn_accum[3, nlvinprof + nmandlvls, 1] = nrlacqc_pc
                            zevn_accum[4, nlvinprof + nmandlvls, 1] = 98
# u and v components of wind
                        if ibfms[wuvevn_accum[1, jj, 1]] == 0 and ibfms[wuvevn_accum[1, jjp1, 1]] == 0 and ibfms[wuvevn_accum[2, jj, 1]] == 0 and ibfms[wuvevn_accum[2, jjp1, 1]] == 0:
                            for iii in range(mxe4prof, 0, -1):
                                if ibfms[wuvevn_accum[1, jj, iii]] != 0 or ibfms[wuvevn_accum[2, jj, iii]] != 0:
                                    nevents_w = iii
                                else:
                                    nevents_w = iii
                                    break
                            ull = wuvevn_accum[1, jj, nevents_w]
                            vll = wuvevn_accum[2, jj, nevents_w]
                            uvqll = wuvevn_accum[3, jj, nevents_w]
                            for iii in range(mxe4prof, 0, -1):
                                if ibfms[wuvevn_accum[1, jjp1, iii]] != 0 or ibfms[wuvevn_accum[2, jjp1, iii]] != 0:
                                    nevents_w = iii
                                else:
                                    nevents_w = iii
                                    break
                            uul = wuvevn_accum[1, jjp1, nevents_w]
                            vul = wuvevn_accum[2, jjp1, nevents_w]
                            uvqul = wuvevn_accum[3, jjp1, nevents_w]
                            du_dlnp = (uul - ull) / alog(pul / pll)
                            dv_dlnp = (vul - vll) / alog(pul / pll)
                            uml = ull + (du_dlnp * (alog(pml / pll)))
                            vml = vll + (dv_dlnp * (alog(pml / pll)))
                            wuvevn_accum[1, nlvinprof + nmandlvls, 1] = uml
                            wuvevn_accum[2, nlvinprof + nmandlvls, 1] = vml
                            wuvevn_accum[3, nlvinprof + nmandlvls, 1] = max(uvqll, uvqul)
                            wuvevn_accum[4, nlvinprof + nmandlvls, 1] = nrlacqc_pc
                            wuvevn_accum[5, nlvinprof + nmandlvls, 1] = 98
        nlv2wrt_tot = nlvinprof + nmandlvls

# Re-sort pressures (now with mandatory levels inclded) from lowest to highest
        orders(1, iwork, lvlsinprof, iord, nlv2wrt_tot, 1, lwr, 2)

### NickE what do i do with write 41)
    print('nlv2wrt_tot=', nlv2wrt_tot, 'c_acftreg=', c_acftreg1)
    err_tspline = 0

#### where 3 ended and 4 began

# Calculate vertical velocity rate_accum
# add ascent/descent rate here

    if ((nlv2wrt_tot > 1) and tsplines):
        nh = 0
        for j in range(1, nlv2wrt_tot + 1):
            jj = iord[j]
            if (ibfms[drinfo_accum[3, jj]] == 0):
                nh += 1
        nh2 = nh * 2
        halfgate = 30.0
        print('halfgate=', halfgate)
        idx = [0] * nh
        pof = [0] * nh
        tdata = [0] * nh
        hdata = [0] * nh
        wdata = [0] * nh
        te = [0] * nh
        hgts = [0] * nh
        hs = [0] * nh
        dhdt = [0] * nh
        maxita = 0
        maxitb = 0
        maxrts = 0
        maxit = 0
        nh = 0
        for j in range(1, nlv2wrt_tot + 1):
            jj = iord[j]
            if (ibfms[drinfo_accum[3, jj]] == 0):
                nh += 1
                tdata[nh] = drinfo_accum[3, jj]
                hdata[nh] = zevn_accum[1, jj, 1]
                pof[nh] = int(acft_seq_accum[2, jj])
                print('tdata,hdata,pof=', nh, tdata[nh], hdata[nh], pof[nh])

# arrange data with time increase
# NickE
        convertd(nh, halfgate, tdata, hdata, pof, doru, idx, hgts, hs, descending, FF)
        if not (FF):
            if (descending):
                print('set descending')
            else:
                print('set ascending')
#NickE
            count_gates(nh, hgts[0:nh], mh)
            m = mh * 2
            hgtp = [0] * m
            hp = [0] * m
            qbest = [0] * m
            habest = [0] * m
            modebest = [0] * mh
#NickE
            best_slalom(nh, mh, doru, hgts, hs, halfgate, bigT, hgtp, hp, qbest, habest, enbest, modebest, maxita, maxitb, maxit, maxrts, FF)
            print('maxita,maxitb,maxit,maxrts=', maxita, maxitb, maxit, maxrts)
            if not (FF):
#NickE
                bnewton(nh, m, bigT, halfgate, hgts, hs, hgtp, habest, qbest, te[0:nh], dhdt[0:nh], FF)
                if not (FF):
#NickE
                    convertd_back(nh, halfgate, wdata, tdata, dhdt, hgts, idx, descending)
                    for j in range(1, nh + 1):
                        print('hgts,hs,dhdt,wdata=', j, hgts[j], hs[j], dhdt[j], wdata[j])
                    nh = 0
# Encode dhdt into PREPBUFR-like file as IALR
                    for j in range(1, nlv2wrt_tot + 1):
                        jj = iord[j]
                        if (ibfms[drinfo_accum[3, jj]] == 0):
                            nh += 1
                            rate_accum[jj] = wdata[nh]
                            print('j,z,rate=', j, zevn_accum[1, jj, 1], rate_accum[jj])

                else:
                    print("WARNING: tspline err in utility pspl, coming out of subr. convertd - use finite difference method")
                    err_tspline = 1
            else:
                print("WARNING: tspline err in utility pspl, coming out of subr. best_slalom - use finite difference method")
                err_tspline = 1
        else:
            print("WARNING: tspline err in utility pspl, coming out of subr. bnewton - use finite difference method")
            err_tspline = 1

    if (allocated(idx)):
        del idx
    if (allocated(pof)):
        del pof
    if (allocated(tdata)):
        del tdata
    if (allocated(hdata)):
        del hdata
    if (allocated(wdata)):
        del wdata
    if (allocated(te)):
        del te
    if (allocated(hgts)):
        del hgts
    if (allocated(hs)):
        del hs
    if (allocated(dhdt)):
        del dhdt
    if (allocated(hgtp)):
        del hgtp
    if (allocated(hp)):
        del hp
    if (allocated(qbest)):
        del qbest
    if (allocated(habest)):
        del habest
    if (allocated(modebest)):
        del modebest

    if (((nlv2wrt_tot > 1) and (not tsplines)) or (err_tspline > 0)):
        for j in range(1, nlv2wrt_tot + 1):
            jj = iord[j]
            print('j,ord,z,t,pof=', j, jj, zevn_accum[1, jj, 1], drinfo_accum[3, jj], acft_seq_accum[1, jj], acft_seq_accum[2, jj])
        for j in range(1, nlv2wrt_tot + 1):
            jj = iord[j]
            jkp = 0
            jkm = 0
            jjp1 = 0
            jjm1 = 0
            if (j == nlv2wrt_tot):
                if (ibfms[drinfo_accum[3, jj]] == 0):
                    jjp1 = jj
                    jkp = j
            else:
                for jk in range(j + 1, nlv2wrt_tot + 1):
                    jjp = iord[jk]
                    if (jjp > nlvinprof):
                        continue
                    if (ibfms[drinfo_accum[3, jjp]] == 0):
                        jjp1 = jjp
                        jkp = jk
                        break
            if (j == 1):
                if (ibfms[drinfo_accum[3, jj]] == 0):
                    jjm1 = jj
                    jkm = j
            else:
                for jk in range(j - 1, 0, -1):
                    jjm = iord[jk]
                    if (jjm > nlvinprof): # Use real obs only
                        continue
                    if (ibfms[drinfo_accum[3, jjm]] == 0):
                        jjm1 = jjm
                        jkm = jk
                        break
            if ((jjp1 != 0) and (jjm1 != 0)):
                dt = (drinfo_accum[3, jjp1] - drinfo_accum[3, jjm1]) * 3600.
                c1_jk = 0
                c2_jk = 0
                while ((abs(dt) < 60.) and ((jkp + c1_jk <= nlv2wrt_tot) or (jkm - c2_jk >= 1))):
                    jjp2 = 0
                    jjm2 = 0
                    c1_jk += 1
                    c2_jk += 1
                    dt_new = dt
                    while (jkp + c1_jk <= nlv2wrt_tot and iord[jkp + c1_jk] > nlvinprof):
                        c1_jk += 1   #skip mandatory level
                    if (jkp + c1_jk <= nlv2wrt_tot and iord[jkp + c1_jk] <= nlvinprof):
                        jjp = iord[jkp + c1_jk]
                        if (ibfms[drinfo_accum[3, jjp]] == 0):
                            jjp2 = jjp
                            dt_new = (drinfo_accum[3, jjp2] - drinfo_accum[3, jjm1]) * 3600.
                    if (abs(dt_new) >= 60.):
                        if (jjp2 != 0):
                            jjp1 = jjp2
                        break
                    while (jkm - c2_jk >= 1 and iord[jkm - c2_jk] > nlvinprof):
                        c2_jk += 1 #skip mandatory level
                    if (jkm - c2_jk >= 1 and iord[jkm - c2_jk] <= nlvinprof):
                        jjm = iord[jkm - c2_jk]
                        if (ibfms[drinfo_accum[3, jjm]] == 0):
                            jjm2 = jjm
                            dt_new = (drinfo_accum[3, jjp1] - drinfo_accum[3, jjm2]) * 3600.
                    if (abs(dt_new) >= 60.):
                        if (jjm2 != 0):
                            jjm1 = jjm2
                        break
                    if ((jjp2 != 0) and (jjm2 != 0)):
                        dt_new = (drinfo_accum[3, jjp2] - drinfo_accum[3, jjm2]) * 3600.
                        if (abs(dt_new) >= 60.):
                            if (jjp2 != 0):
                                jjp1 = jjp2
                            if (jjm2 != 0):
                                jjm1 = jjm2
                            break
                dt = (drinfo_accum[3, jjp1] - drinfo_accum[3, jjm1]) * 3600.
                zul = zevn_accum[1, jjp1, 1]
                zll = zevn_accum[1, jjm1, 1]
                if (abs(dt) > 0.): #avoid divide by 0
                    rate_accum[jj] = (zul - zll) / dt
                print('fj,dt,rate_accum=', j, dt, rate_accum[jj])
                print('')

### where 5 originally started

# Interpolate position and time to mandatory level (will be stored in XDR YDR HRDR) (need to
# have mandatory levels inserted into the profile before this step)

    if (l_mandlvl and nlvinprof > 1):
        for j in range(1, nlv2wrt_tot + 1):
            jj = iord[j]
            nmNbtw = 0
            if (ibfms[drinfo_accum[1, jj]] != 0 and
                ibfms[drinfo_accum[2, jj]] != 0 and
                ibfms[drinfo_accum[3, jj]] != 0):
# all obs in drift sequence missing likely  means this is a mandatory level for
# which these obs must be filled via interpolation
                nmNbtw = 1  #reset 'number of mandatory levels in-between' counter
# see if there is more than one mandatory level in a row for which we need to calculate XDR,
# YDR and HRDR values
                for k in range(j + 1, nlv2wrt_tot + 1):
                    kk = iord[k]
                    if (ibfms[drinfo_accum[1, kk]] != 0 and
                        ibfms[drinfo_accum[2, kk]] != 0 and
                        ibfms[drinfo_accum[3, kk]] != 0):
#another mandatory levelw/ missing XDR, YDR and HRDR
                        nmNbtw = nmNbtw + 1
                    else:
                        break

# At this point, nmNbtw is the number of mandatory levels in a row w/ missing XDR, YDR and
# HRDR - ow we need to determine the "bread" levels; in other words, levels with real, non-
# interpolated data, that sandwich the mandatory levels - below, jj points to the mandatory
# level, jjm1 points to the "bread" level with actual data at the lower pressure/higher
# altitude and jjpnmNbtw points to the "bread" level with actual data at a higher pressure/
# lower altitude
                if (j <= 1):
                    print('### PROBLEM - j <= 1 (=', j, ') in subr. ',
                          'sub2mem_mer, iord array underflow')
                    print('              this should never happen')
#NickE
                    w3tage('PREPOBS_PREPACQC')
                    errexit(61)
                jjm1 = iord[j - 1]
                jjpnmNbtw = iord[j + nmNbtw]
                pll = lvlsinprof[jjm1]
                pul = lvlsinprof[jjpnmNbtw]
# Interpolate lat/lon/time to mandatory levels
# Determine dtime/dlnp, total horizontal distance covered between the two points, and average
#  groundspeed of aircraft between the points
                dtime_dlnp = (drinfo_accum[3, jjpnmNbtw] -
                              drinfo_accum[3, jjm1]) / log(pul / pll)
# Use Haversine formula to determine distance, given two lat/lons (the same formula is used
# in the acftobs_qc/gcirc_qc routine and more information is available at
# http://www.movable-type.co.uk/scripts/GIS-FAQ-5.1.html)
                lat_pul = drinfo_accum[2, jjpnmNbtw]
                lon_pul = drinfo_accum[1, jjpnmNbtw]
                lat_pll = drinfo_accum[2, jjm1]
                lon_pll = drinfo_accum[1, jjm1]
                if (int(lon_pul * 100) == int(lon_pll * 100)):
                    dist_pul_pll = radius_e * abs(lat_pul - lat_pll) * deg2rad
                elif (int(lat_pul * 100) == int(lat_pll * 100)):
                    dist_pul_pll = 2.0 * radius_e * asin(min(1.0, abs(cos(lat_pul * deg2rad) *
                                                                       sin((lon_pul - lon_pll) * 0.5 * deg2rad))))
                else:
                    dist_pul_pll = 2.0 * radius_e * asin(min(1.0, sqrt(
                        (sin((lat_pul - lat_pll) * 0.5 * deg2rad)) ** 2
                        + cos(lat_pul * deg2rad) *
                        cos(lat_pll * deg2rad) *
                        (sin((lon_pul - lon_pll) * 0.5 * deg2rad)) ** 2
                    )))
# Check if times are equal, then interpolate lat/lon - assume aircraft is traveling at a
# constant speed between the locations where pul and pll are observed
                if (int(drinfo_accum[3, jjpnmNbtw] * 100000) != int(drinfo_accum[3, jjm1] * 100000) and
                    dist_pul_pll != 0):
                    spd_pul_pll = dist_pul_pll / abs((drinfo_accum[3, jjpnmNbtw] -
                                                      drinfo_accum[3, jjm1]) * 3600)
                    for k in range(nmNbtw):
                        jjpk = iord[j + k]
                        pml = lvlsinprof[jjpk]
# time
                        drinfo_accum[3, jjpk] = drinfo_accum[3, jjm1] + dtime_dlnp * log(pml / pll)
                        dist2pml = spd_pul_pll * abs(drinfo_accum[3, jjpk] - drinfo_accum[3, jjm1]) * 3600
# lat
                        drinfo_accum[2, jjpk] = drinfo_accum[2, jjm1] + dist2pml / dist_pul_pll * (
                                drinfo_accum[2, jjpnmNbtw] - drinfo_accum[2, jjm1])
# lon
                        drinfo_accum[1, jjpk] = drinfo_accum[1, jjm1] + dist2pml / dist_pul_pll * (
                                drinfo_accum[1, jjpnmNbtw] - drinfo_accum[1, jjm1])
                else:
# ! times are equal; assume groundspeed varies linearly -- or, dist_pul_pll=0
# and lat/lons of pul and pll are either equal or very very close
                    delx = (drinfo_accum[1, jjpnmNbtw] -
                            drinfo_accum[1, jjm1]) / (nmNbtw + 1)
                    dely = (drinfo_accum[2, jjpnmNbtw] -
                            drinfo_accum[2, jjm1]) / (nmNbtw + 1)
# Store interpolated lat/lon/time values for the levels that need it
                    for k in range(nmNbtw):
                        jjpk = iord[j + k]
                        pml = lvlsinprof[jjpk]
                        drinfo_accum[1, jjpk] = drinfo_accum[1, jjm1] + (k + 1) * delx
                        drinfo_accum[2, jjpk] = drinfo_accum[2, jjm1] + (k + 1) * dely
                        drinfo_accum[3, jjpk] = drinfo_accum[3, jjm1] + dtime_dlnp * log(pml / pll)

# Set TYP to reflect whether or not report is part of a profile, ascending or descending
        jjmaxp = iord[nlv2wrt_tot]
        jjminp = iord[1]
        if (nlv2wrt_tot == 1):
            hdr2wrt[6] = 300 + (int(hdr2wrt[6]) % 100)
        elif (nlv2wrt_tot > 1 and
              (c_qc_accum[jjmaxp][10] == 'a' or
               c_qc_accum[jjmaxp][10] == 'A')):
# Make sure the header information for the ascent is the coordinates, etc, present at the
# "launch" level (highest pressure/lowest altitude)
            hdr2wrt[6] = 400 + (int(hdr2wrt[6]) % 100)
            hdr2wrt[2] = drinfo_accum[1, jjmaxp]
            hdr2wrt[3] = drinfo_accum[2, jjmaxp]
            hdr2wrt[4] = drinfo_accum[3, jjmaxp]
            hdr2wrt[5] = elv_accum[1, jjmaxp]
            hdr2wrt[12] = rpt_accum[1, jjmaxp]
            hdr2wrt[13] = tcor_accum[1, jjmaxp]
        elif (nlv2wrt_tot > 1 and
# Make sure the header information for the descent is the coordinates, etc., present at the
# "launch" level (lowest pressure/highest altitude)
              (c_qc_accum[jjmaxp][10] == 'd' or
               c_qc_accum[jjmaxp][10] == 'D')):
            hdr2wrt[6] = 500 + (int(hdr2wrt[6]) % 100)
            hdr2wrt[2] = drinfo_accum[1, jjminp]
            hdr2wrt[3] = drinfo_accum[2, jjminp]
            hdr2wrt[4] = drinfo_accum[3, jjminp]
            hdr2wrt[5] = elv_accum[1, jjminp]
            hdr2wrt[12] = rpt_accum[1, jjminp]
            hdr2wrt[13] = tcor_accum[1, jjminp]
# Set SQN/PROCN to missing for profiles
        hdr2wrt[10] = bmiss   # NickE
        hdr2wrt[11] = bmiss   # NickE

#line 1347 of sub2mem_mer.f
# The next section of the sub2mem_mer.f code writes header info and all that to the
# prepbufr so I don't think I need it
