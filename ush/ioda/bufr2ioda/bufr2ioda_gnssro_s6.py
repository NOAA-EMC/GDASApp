#!/usr/bin/env python3
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
import os
import argparse
import json
import numpy as np
import numpy.ma as ma
import math
import calendar
import time
import datetime
from pyiodaconv import bufr
from collections import namedtuple
from pyioda import ioda_obs_space as ioda_ospace
from wxflow import Logger

# ====================================================================
# GPS-RO BUFR dump file
# =====================================================================
# NC003010  |    GPS-RO
# ====================================================================


def Derive_stationIdentification(said, ptid):

    stid = []
    for i in range(len(said)):
        newval = str(said[i]).zfill(4)+str(ptid[i]).zfill(4)
        stid.append(str(newval))
    stid = np.array(stid).astype(dtype='str')
    stid = ma.array(stid)
    ma.set_fill_value(stid, "")

    return stid


def Compute_Grid_Location(degrees):

    for i in range(len(degrees)):
        if degrees[i] <= 360 and degrees[i] >= -180:
            degrees[i] = np.deg2rad(degrees[i])
    rad = degrees

    return rad


def Compute_imph(impp, elrc, geodu):

    imph = (impp - elrc - geodu).astype(np.float32)

    return imph


def bufr_to_ioda(config, logger):

    subsets = config["subsets"]
    logger.debug(f"Checking subsets = {subsets}")

    # =========================================
    # Get parameters from configuration
    # =========================================
    data_format = config["data_format"]
    data_type = config["data_type"]
    ioda_data_type = "gnssro"
    data_description = config["data_description"]
    data_provider = config["data_provider"]
    cycle_type = config["cycle_type"]
    dump_dir = config["dump_directory"]
    ioda_dir = config["ioda_directory"]
    mission = config["mission"]
    satellite_info_array = config["satellite_info"]
    cycle = config["cycle_datetime"]
    yyyymmdd = cycle[0:8]
    hh = cycle[8:10]

    bufrfile = f"{cycle_type}.t{hh}z.{data_type}.tm00.{data_format}"
    DATA_PATH = os.path.join(dump_dir, f"{cycle_type}.{yyyymmdd}", str(hh),
                             'atmos', bufrfile)

    # ============================================
    # Make the QuerySet for all the data we want
    # ============================================
    start_time = time.time()

    logger.debug(f"Making QuerySet ...")
    q = bufr.QuerySet(subsets)

    # MetaData
    q.add('latitude', '*/ROSEQ1/CLATH')
    q.add('longitude', '*/ROSEQ1/CLONH')
    q.add('gridLatitude', '*/ROSEQ1/CLATH')
    q.add('gridLongitude', '*/ROSEQ1/CLONH')
    q.add('year', '*/YEAR')
    q.add('year2', '*/YEAR')
    q.add('month', '*/MNTH')
    q.add('day', '*/DAYS')
    q.add('hour', '*/HOUR')
    q.add('minute', '*/MINU')
    q.add('second', '*/SECO')
    q.add('satelliteIdentifier', '*/SAID')
    q.add('satelliteInstrument', '*/SIID')
    q.add('satelliteConstellationRO', '*/SCLF')
    q.add('satelliteTransmitterId', '*/PTID')
    q.add('earthRadiusCurvature', '*/ELRC')
    q.add('sequenceNumber', '*/SEQNUM')
    q.add('geoidUndulation', '*/GEODU')
    q.add('height', '*/ROSEQ3/HEIT')
    q.add('impactParameterRO_roseq2repl1', '*/ROSEQ1/ROSEQ2{1}/IMPP')
    q.add('impactParameterRO_roseq2repl2', '*/ROSEQ1/ROSEQ2{2}/IMPP')
    q.add('impactParameterRO_roseq2repl3', '*/ROSEQ1/ROSEQ2{3}/IMPP')
    q.add('frequency__roseq2repl1', '*/ROSEQ1/ROSEQ2{1}/MEFR')
    q.add('frequency__roseq2repl2', '*/ROSEQ1/ROSEQ2{2}/MEFR')
    q.add('frequency__roseq2repl3', '*/ROSEQ1/ROSEQ2{3}/MEFR')
#    q.add('pccf', '*/ROSEQ1/PCCF')
    q.add('pccf', '*/PCCF[1]')
    q.add('percentConfidence', '*/ROSEQ3/PCCF')
    q.add('sensorAzimuthAngle', '*/BEARAZ')

    # Processing Center
    q.add('dataProviderOrigin', '*/OGCE')

    # Quality Information
    q.add('qualityFlags', '*/QFRO')
    q.add('qfro', '*/QFRO')
    q.add('satelliteAscendingFlag', '*/QFRO')

    # ObsValue
    q.add('bendingAngle_roseq2repl1', '*/ROSEQ1/ROSEQ2{1}/BNDA[1]')
    q.add('bendingAngle_roseq2repl2', '*/ROSEQ1/ROSEQ2{2}/BNDA[1]')
    q.add('bendingAngle_roseq2repl3', '*/ROSEQ1/ROSEQ2{3}/BNDA[1]')
    q.add('atmosphericRefractivity', '*/ROSEQ3/ARFR[1]')

    # ObsError
    q.add('obsErrorBendingAngle1', '*/ROSEQ1/ROSEQ2{1}/BNDA[2]')
    q.add('obsErrorBendingAngle2', '*/ROSEQ1/ROSEQ2{2}/BNDA[2]')
    q.add('obsErrorBendingAngle3', '*/ROSEQ1/ROSEQ2{3}/BNDA[2]')
    q.add('obsErrorAtmosphericRefractivity', '*/ROSEQ3/ARFR[2]')

    # ObsType
    q.add('obsTypeBendingAngle', '*/SAID')
    q.add('obsTypeAtmosphericRefractivity', '*/SAID')

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for making QuerySet: {running_time} seconds")

    # ==============================================================
    # Open the BUFR file and execute the QuerySet to get ResultSet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

    logger.debug(f"Executing QuerySet to get ResultSet ...")
    with bufr.File(DATA_PATH) as f:
        r = f.execute(q)

    logger.debug(f" ... Executing QuerySet: get MetaData: basic ...")
    # MetaData
    clath = r.get('latitude', 'latitude')
    clonh = r.get('longitude', 'latitude')
    gclath = r.get('gridLatitude', 'latitude')
    gclonh = r.get('gridLongitude', 'latitude')
    year = r.get('year', 'latitude')
    year2 = r.get('year2')
    mnth = r.get('month', 'latitude')
    days = r.get('day', 'latitude')
    hour = r.get('hour', 'latitude')
    minu = r.get('minute', 'latitude')
    seco = r.get('second', 'latitude')
    said = r.get('satelliteIdentifier', 'latitude')
    siid = r.get('satelliteInstrument', 'latitude')
    sclf = r.get('satelliteConstellationRO', 'latitude')
    ptid = r.get('satelliteTransmitterId', 'latitude')
    elrc = r.get('earthRadiusCurvature', 'latitude')
    seqnum = r.get('sequenceNumber', 'latitude')
    geodu = r.get('geoidUndulation', 'latitude')
    heit = r.get('height', 'height', type='float32').astype(np.float32)
    impp1 = r.get('impactParameterRO_roseq2repl1', 'latitude')
    impp2 = r.get('impactParameterRO_roseq2repl2', 'latitude')
    impp3 = r.get('impactParameterRO_roseq2repl3', 'latitude')
#    impp1 = r.get('impactParameterRO_roseq2repl1', 'latitude', type='double')
#    impp2 = r.get('impactParameterRO_roseq2repl2', 'latitude', type='double')
#    impp3 = r.get('impactParameterRO_roseq2repl3', 'latitude', type='double')


#    for i in range(len(said)):
#        if (said[i] == 42.0):
#            logger.debug(f"xuanli check impp1, impp2, impp3 {impp1[i]}, {impp2[i]}, {impp3[i]}")

    mefr1 = r.get('frequency__roseq2repl1', 'latitude',
                  type='float32').astype(np.float32)
    mefr2 = r.get('frequency__roseq2repl2', 'latitude',
                  type='float32').astype(np.float32)
    mefr3 = r.get('frequency__roseq2repl3', 'latitude',
                  type='float32').astype(np.float32)
    pccf = r.get('pccf', 'latitude', type='float32').astype(np.float32)
    ref_pccf = r.get('percentConfidence', 'height')
    bearaz = r.get('sensorAzimuthAngle', 'latitude')

    logger.debug(f" ... Executing QuerySet: get MetaData: processing center...")
    # Processing Center
    ogce = r.get('dataProviderOrigin', 'latitude')

    logger.debug(f" ... Executing QuerySet: get metadata: data quality \
                information ...")
    # Quality Information
    qfro = r.get('qualityFlags', 'latitude')
    qfro2 = r.get('pccf', 'latitude', type='float32').astype(np.float32)
    satasc = r.get('satelliteAscendingFlag', 'latitude')

    logger.debug(f" ... Executing QuerySet: get ObsValue: Bending Angle ...")
    # ObsValue
    # Bending Angle
    bnda1 = r.get('bendingAngle_roseq2repl1', 'latitude')
    bnda2 = r.get('bendingAngle_roseq2repl2', 'latitude')
    bnda3 = r.get('bendingAngle_roseq2repl3', 'latitude')
    arfr = r.get('atmosphericRefractivity', 'height')

    # ObsError
    # Bending Angle
    bndaoe1 = r.get('obsErrorBendingAngle1', 'latitude')
    bndaoe2 = r.get('obsErrorBendingAngle2', 'latitude')
    bndaoe3 = r.get('obsErrorBendingAngle3', 'latitude')
    arfroe = r.get('obsErrorAtmosphericRefractivity', 'height')

    # assign sequenceNumber (SEQNUM in the bufr table is less than 1,000 and used repeatedly)
    logger.debug(f"Assign sequence number: starting from 1")
#    logger.debug(f"     seqnum shape, type, min/max {seqnum.shape}, \
#                {seqnum.dtype}, {seqnum.min()}, {seqnum.max()}")

    count1 = 0
    count2 = 0
    seqnum2 = []
    for i in range(len(seqnum)):
        if (int(seqnum[i]) != count2):
            count1 += 1
        count2 = int(seqnum[i])
        seqnum2.append(count1)
    seqnum2 = np.array(seqnum2)

    logger.debug(f"     new seqnum2 shape, type, min/max {seqnum2.shape}, \
                {seqnum2.dtype}, {seqnum2.min()}, {seqnum2.max()}")

    # ObsType
    # Bending Angle
    bndaot = r.get('obsTypeBendingAngle', 'latitude')
    arfrot = r.get('obsTypeBendingAngle', 'latitude')

    logger.debug(f" ... Executing QuerySet: get datatime: observation time ...")
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    timestamp = r.get_datetime('year', 'month', 'day', 'hour', 'minute',
                               'second', 'latitude').astype(np.int64)

    logger.debug(f" ... Executing QuerySet: Done!")

    logger.debug(f" ... Executing QuerySet: Check BUFR variable generic \
                dimension and type ...")
    # Check BUFR variable generic dimension and type
    logger.debug(f"     clath     shape, type = {clath.shape}, {clath.dtype}")
    logger.debug(f"     clonh     shape, type = {clonh.shape}, {clonh.dtype}")
    logger.debug(f"     gclath    shape, type = {gclath.shape}, {gclath.dtype}")
    logger.debug(f"     gclonh    shape, type = {gclonh.shape}, {gclonh.dtype}")
    logger.debug(f"     year      shape, type = {year.shape}, {year.dtype}")
    logger.debug(f"     mnth      shape, type = {mnth.shape}, {mnth.dtype}")
    logger.debug(f"     days      shape, type = {days.shape}, {days.dtype}")
    logger.debug(f"     hour      shape, type = {hour.shape}, {hour.dtype}")
    logger.debug(f"     minu      shape, type = {minu.shape}, {minu.dtype}")
    logger.debug(f"     seco      shape, type = {seco.shape}, {seco.dtype}")
    logger.debug(f"     said      shape, type = {said.shape}, {said.dtype}")
    logger.debug(f"     siid      shape, type = {siid.shape}, {siid.dtype}")
    logger.debug(f"     sclf      shape, type = {sclf.shape}, {sclf.dtype}")
    logger.debug(f"     ptid      shape, type = {ptid.shape}, {ptid.dtype}")
    logger.debug(f"     elrc      shape, type = {elrc.shape}, {elrc.dtype}")
    logger.debug(f"     seqnum    shape, type = {seqnum.shape}, {seqnum.dtype}")
    logger.debug(f"     geodu     shape, type = {geodu.shape}, {geodu.dtype}")
    logger.debug(f"     heit      shape, type = {heit.shape}, {heit.dtype}")
    logger.debug(f"     impp1     shape, type = {impp1.shape}, {impp1.dtype}")
    logger.debug(f"     impp2     shape, type = {impp2.shape}, {impp2.dtype}")
    logger.debug(f"     impp3     shape, type = {impp3.shape}, {impp3.dtype}")
    logger.debug(f"     mefr1     shape, type = {mefr1.shape}, {mefr1.dtype}")
    logger.debug(f"     mefr3     shape, type = {mefr3.shape}, {mefr3.dtype}")
    logger.debug(f"     pccf      shape, type = {pccf.shape}, {pccf.dtype}")
    logger.debug(f"     pccf      shape, fill = {pccf.fill_value}")
    logger.debug(f"     ref_pccf  shape, type = {ref_pccf.shape}, \
                {ref_pccf.dtype}")
    logger.debug(f"     bearaz    shape, type = {bearaz.shape}, {bearaz.dtype}")

    logger.debug(f"     ogce      shape, type = {ogce.shape}, {ogce.dtype}")

    logger.debug(f"     qfro      shape, type = {qfro.shape}, {qfro.dtype}")
    logger.debug(f"     satasc    shape, type = {satasc.shape}, {satasc.dtype}")

    logger.debug(f"     bnda1     shape, type = {bnda1.shape}, {bnda1.dtype}")
    logger.debug(f"     bnda3     shape, type = {bnda3.shape}, {bnda3.dtype}")
    logger.debug(f"     arfr      shape, type = {arfr.shape}, {arfr.dtype}")

    logger.debug(f"     bndaoe1   shape, type = {bndaoe1.shape}, \
                {bndaoe1.dtype}")
    logger.debug(f"     bndaoe3   shape, type = {bndaoe3.shape}, \
                {bndaoe3.dtype}")
    logger.debug(f"     arfroe    shape, type = {arfr.shape}, {arfr.dtype}")

    logger.debug(f"     bndaot    shape, type = {bndaot.shape}, {bndaot.dtype}")

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for executing QuerySet to get ResultSet: \
                {running_time} seconds")

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.debug(f"Creating derived variables - stationIdentification")
    stid = Derive_stationIdentification(said, ptid)

    logger.debug(f"     stid shape,type = {stid.shape}, {stid.dtype}")

    logger.debug(f"Creating derived variables - Grid Latitude / Longitude ...")
    gclonh = Compute_Grid_Location(gclonh)
    gclath = Compute_Grid_Location(gclath)

    logger.debug(f"     gclonh shape,type = {gclonh.shape}, {gclonh.dtype}")
    logger.debug(f"     gclath shape,type = {gclath.shape}, {gclath.dtype}")
    logger.debug(f"     gclonh min/max = {gclonh.min()}, {gclonh.max()}")
    logger.debug(f"     gclath min/max = {gclath.min()}, {gclath.max()}")

    logger.debug(f"Creating derived variables - imph ...")

    imph1 = Compute_imph(impp1, elrc, geodu)
    imph2 = Compute_imph(impp2, elrc, geodu)
    imph3 = Compute_imph(impp3, elrc, geodu)

    logger.debug(f"     imph1 shape,type = {imph1.shape}, {imph1.dtype}")
    logger.debug(f"     imph3 shape,type = {imph3.shape}, {imph3.dtype}")
    logger.debug(f"     imph1 min/max = {imph1.min()}, {imph1.max()}")
    logger.debug(f"     imph3 min/max = {imph3.min()}, {imph3.max()}")

    logger.debug(f"Keep bending angle with Freq = 0.0")
    for i in range(len(said)):
        if (mefr2[i] == 0.0):
            bnda1[i] = bnda2[i]
#            mefr1[i] = mefr2[i]
            impp1[i] = impp2[i]
            imph1[i] = imph2[i]
            bndaoe1[i] = bndaoe2[i]
        if (mefr3[i] == 0.0):
            bnda1[i] = bnda3[i]
#            mefr1[i] = mefr3[i]
            impp1[i] = impp3[i]
            imph1[i] = imph3[i]
            bndaoe1[i] = bndaoe3[i]

    logger.debug(f"     new bnda1 shape, type, min/max {bnda1.shape}, \
                {bnda1.dtype}, {bnda1.min()}, {bnda1.max()}")
    logger.debug(f"     new mefr1 shape, type, min/max {mefr1.shape}, \
                {mefr1.dtype}, {mefr1.min()}, {mefr1.max()}")
    logger.debug(f"     mefr2 shape, type, min/max {mefr2.shape}, \
                {mefr2.dtype}, {mefr2.min()}, {mefr2.max()}")
    logger.debug(f"     mefr3 shape, type, min/max {mefr3.shape}, \
                {mefr3.dtype}, {mefr3.min()}, {mefr3.max()}")
    logger.debug(f"     new impp1 shape, type, min/max {impp1.shape}, \
                {impp1.dtype}, {impp1.min()}, {impp1.max()}")
    logger.debug(f"     new imph1 shape, type, min/max {imph1.shape}, \
                {imph1.dtype}, {imph1.min()}, {imph1.max()}")
    logger.debug(f"     new bndaoe1 shape, type, min/max {bndaoe1.shape}, \
                {bndaoe1.dtype}, {bndaoe1.min()}, {bndaoe1.max()}")

#   find ibit for qfro (16bit from left to right)
#   if bit5=1 the reject the bending angle obs
#   if bit6=1 the reject the refractivity obs
    bit3 = []
    bit5 = []
    bit6 = []
    for quality in qfro:
        if quality & 8192 > 0:
            bit3.append(1)
        else:
            bit3.append(0)

        if quality & 2048 > 0:
            bit5.append(1)
        else:
            bit5.append(0)

        # For refractivity data use only:
        if quality & 1024 > 0:
            bit6.append(1)
        else:
            bit6.append(0)

    bit3 = np.array(bit3)
    bit5 = np.array(bit5)
    bit6 = np.array(bit6)
    logger.debug(f"     new bit3 shape, type, min/max {bit3.shape}, \
                {bit3.dtype}, {bit3.min()}, {bit3.max()}")

#   overwrite satelliteAscendingFlag and QFRO
    for quality in range(len(bit3)):
        satasc[quality] = 0
        qfro2[quality] = 0.0
        if bit3[quality] == 1:
            satasc[quality] = 1
        # if (bit6[quality] == 1): refractivity data only
        #    qfro2[quality] = 1.0
        if (bit5[quality] == 1):
            qfro2[quality] = 1.0

    logger.debug(f"     new satasc shape, type, min/max {satasc.shape}, \
                {satasc.dtype}, {satasc.min()}, {satasc.max()}")
    logger.debug(f"     new qfro2 shape, type, min/max {qfro2.shape}, \
                {qfro2.dtype}, {qfro2.min()}, {qfro2.max()}, {qfro2.fill_value}")
    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for creating derived variables: {running_time} \
                seconds")

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    # Find unique satellite identifiers in data to process
    mission_said = []
    for sensor_satellite_info in satellite_info_array:
        mission_said.append(float(sensor_satellite_info["satellite_id"]))
    mission_said = np.array(mission_said)

    unique_satids = np.unique(said)
    logger.debug(f" ... Number of Unique satellite identifiers: \
                {len(unique_satids)}")
    logger.debug(f" ... Unique satellite identifiers: {unique_satids}")

    print(' ... Number of Unique satellite identifiers: ', len(unique_satids))
    print(' ... Unique satellite identifiers: ', unique_satids)
    print(' ... mission_said: ', mission_said)

    print(' ... Loop through unique satellite identifier ... : ', unique_satids)

    nobs = 0
    for sat in unique_satids.tolist():
        print("Processing output for said: ", sat)
        start_time = time.time()

        # Find matched sensor_satellite_info from sensor_satellite_info namedtuple
        matched = False
        for sensor_satellite_info in satellite_info_array:
            if (sensor_satellite_info["satellite_id"] == sat):

                matched = True
                sensor_id = sensor_satellite_info["sensor_id"]
                sensor_name = sensor_satellite_info["sensor_name"]
                sensor_full_name = sensor_satellite_info["sensor_full_name"]
                satellite_id = sensor_satellite_info["satellite_id"]
                satellite_name = sensor_satellite_info["satellite_name"]
                satellite_full_name = sensor_satellite_info["satellite_full_name"]

        if matched:

            print(' ... Split data for satellite mission ', mission)

            # Define a boolean mask to subset data from the original data object
            mask = np.isin(said, mission_said)

            # MetaData
            clonh_sat = clonh[mask]
            clath_sat = clath[mask]
            gclonh_sat = gclonh[mask]
            gclath_sat = gclath[mask]
            timestamp_sat = timestamp[mask]
            stid_sat = stid[mask]
            said_sat = said[mask]
            siid_sat = siid[mask]
            sclf_sat = sclf[mask]
            ptid_sat = ptid[mask]
            elrc_sat = elrc[mask]
            seqnum2_sat = seqnum2[mask]
            geodu_sat = geodu[mask]
            heit_sat = heit[mask]
            impp1_sat = impp1[mask]
            imph1_sat = imph1[mask]
            mefr1_sat = mefr1[mask]
            pccf_sat = pccf[mask]
            ref_pccf_sat = ref_pccf[mask]
            bearaz_sat = bearaz[mask]
            ogce_sat = ogce[mask]
            qfro_sat = qfro[mask]
            qfro2_sat = qfro2[mask]
            satasc_sat = satasc[mask]
            bnda1_sat = bnda1[mask]
            arfr_sat = arfr[mask]
            bndaoe1_sat = bndaoe1[mask]
            arfroe_sat = arfroe[mask]
            bndaot_sat = bndaot[mask]
            arfrot_sat = arfrot[mask]

            # Processing Center
            ogce_sat = ogce[mask]

            # QC Info
            qfro_sat = qfro[mask]
            qfro2_sat = qfro2[mask]
            satasc_sat = satasc[mask]

            # ObsValue
            bnda1_sat = bnda1[mask]
            arfr_sat = arfr[mask]

            # ObsError
            bndaoe1_sat = bndaoe1[mask]
            arfroe_sat = arfroe[mask]

            # ObsType
            bndaot_sat = bndaot[mask]
            arfrot_sat = arfrot[mask]

            nobs = clath_sat.shape[0]
            print(' ... Create ObsSpace for satid = ', sat)
            print(' ... size location of sat mission = ', nobs)

        # =====================================
        # Create IODA ObsSpace
        # Write IODA output
        # =====================================

        # Create the dimensions
    if nobs > 0:
        dims = {'Location': np.arange(0, nobs)}
        print(' ... dim = ', nobs)
    else:
        dims = {'Location': nobs}
        print(' ... dim = ', nobs)

        # iodafile = f"{cycle_type}.t{hh}z.{data_type}.tm00.{data_format}.nc"
        # iodafile = f"{cycle_type}.t{hh}z.{ioda_data_type}.{mission}.tm00.{data_format}.nc"
    iodafile = f"{cycle_type}.t{hh}z.{ioda_data_type}_{mission}.tm00.nc"

    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)

    print(' ... ... Create OUTPUT file:', OUTPUT_PATH)

    path, fname = os.path.split(OUTPUT_PATH)
    if path and not os.path.exists(path):
        os.makedirs(path)

    # Create IODA ObsSpace
    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    logger.debug(f" ... ... Create global attributes")
    obsspace.write_attr('source_file', bufrfile)
    obsspace.write_attr('dataOriginalFormatSpec', data_format)
    obsspace.write_attr('data_type', data_type)
    obsspace.write_attr('subsets', subsets)
    obsspace.write_attr('cycle_type', cycle_type)
    obsspace.write_attr('cycle_datetime', cycle)
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('data_description', data_description)
    obsspace.write_attr('converter', os.path.basename(__file__))

    if nobs > 0:
        # Create IODA variables
        logger.debug(f" ... ... Create variables: name, type, units, & attributes")
        # Longitude
        obsspace.create_var('MetaData/longitude', dtype=clonh_sat.dtype,
                            fillval=clonh_sat.fill_value) \
            .write_attr('units', 'degrees_east') \
            .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
            .write_attr('long_name', 'Longitude') \
            .write_data(clonh_sat)

        # Latitude
        obsspace.create_var('MetaData/latitude', dtype=clath_sat.dtype,
                            fillval=clath_sat.fill_value) \
            .write_attr('units', 'degrees_north') \
            .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
            .write_attr('long_name', 'Latitude') \
            .write_data(clath_sat)

        # Grid Longitude
        obsspace.create_var('MetaData/gridLongitude', dtype=gclonh_sat.dtype,
                            fillval=gclonh_sat.fill_value) \
            .write_attr('units', 'radians') \
            .write_attr('valid_range', np.array([-3.14159265, 3.14159265],
                        dtype=np.float32)) \
            .write_attr('long_name', 'Grid Longitude') \
            .write_data(gclonh_sat)

        # Grid Latitude
        obsspace.create_var('MetaData/gridLatitude', dtype=gclath_sat.dtype,
                            fillval=gclath_sat.fill_value) \
            .write_attr('units', 'radians') \
            .write_attr('valid_range', np.array([-1.570796325, 1.570796325],
                        dtype=np.float32)) \
            .write_attr('long_name', 'Grid Latitude') \
            .write_data(gclath_sat)

        # Datetime
        obsspace.create_var('MetaData/dateTime', dtype=np.int64,
                            fillval=timestamp_sat.fill_value) \
            .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
            .write_attr('long_name', 'Datetime') \
            .write_data(timestamp_sat)

        # Station Identification
        obsspace.create_var('MetaData/stationIdentification', dtype=stid_sat.dtype,
                            fillval=stid_sat.fill_value) \
            .write_attr('long_name', 'Station Identification') \
            .write_data(stid_sat)

        # Satellite Identifier
        obsspace.create_var('MetaData/satelliteIdentifier', dtype=said_sat.dtype,
                            fillval=said_sat.fill_value) \
            .write_attr('long_name', 'Satellite Identifier') \
            .write_data(said_sat)

        # Satellite Instrument
        obsspace.create_var('MetaData/satelliteInstrument', dtype=siid_sat.dtype,
                            fillval=siid_sat.fill_value) \
            .write_attr('long_name', 'Satellite Instrument') \
            .write_data(siid_sat)

        # Satellite Constellation RO
        obsspace.create_var('MetaData/satelliteConstellationRO', dtype=sclf_sat.dtype,
                            fillval=sclf_sat.fill_value) \
            .write_attr('long_name', 'Satellite Constellation RO') \
            .write_data(sclf_sat)

        # Satellite Transmitter ID
        obsspace.create_var('MetaData/satelliteTransmitterId', dtype=ptid_sat.dtype,
                            fillval=ptid_sat.fill_value) \
            .write_attr('long_name', 'Satellite Transmitter Id') \
            .write_data(ptid_sat)

        # Earth Radius Curvature
        obsspace.create_var('MetaData/earthRadiusCurvature', dtype=elrc_sat.dtype,
                            fillval=elrc_sat.fill_value) \
            .write_attr('units', 'm') \
            .write_attr('long_name', 'Earth Radius of Curvature') \
            .write_data(elrc_sat)

        # Sequence Number
        obsspace.create_var('MetaData/sequenceNumber', dtype=seqnum2_sat.dtype,
                            fillval=said_sat.fill_value) \
            .write_attr('long_name', 'Sequence Number') \
            .write_data(seqnum2_sat)

        # Geoid Undulation
        obsspace.create_var('MetaData/geoidUndulation', dtype=geodu_sat.dtype,
                            fillval=geodu_sat.fill_value) \
            .write_attr('units', 'm') \
            .write_attr('long_name', 'Geoid Undulation') \
            .write_data(geodu_sat)

        # Height
        obsspace.create_var('MetaData/height', dtype=heit_sat.dtype,
                            fillval=heit_sat.fill_value) \
            .write_attr('units', 'm') \
            .write_attr('long_name', 'Height for Atm Refractivity') \
            .write_data(heit_sat)

        # Impact Parameter RO
        obsspace.create_var('MetaData/impactParameterRO', dtype=impp1_sat.dtype,
                            fillval=impp1_sat.fill_value) \
            .write_attr('units', 'm') \
            .write_attr('long_name', 'Impact Parameter Bending Angle') \
            .write_data(impp1_sat)

        # Impact Height RO
        obsspace.create_var('MetaData/impactHeightRO', dtype=imph1_sat.dtype,
                            fillval=imph1_sat.fill_value) \
            .write_attr('units', 'm') \
            .write_attr('long_name', 'Impact Height Bending Angle') \
            .write_data(imph1_sat)

        # Impact Height RO
        obsspace.create_var('MetaData/frequency', dtype=mefr1_sat.dtype,
                            fillval=mefr1_sat.fill_value) \
            .write_attr('units', 'Hz') \
            .write_attr('long_name', 'Frequency') \
            .write_data(mefr1_sat)

        # PCCF Percent Confidence
        obsspace.create_var('MetaData/pccf', dtype=pccf_sat.dtype,
                            fillval=pccf_sat.fill_value) \
            .write_attr('units', '%') \
            .write_attr('long_name', 'Profile Percent Confidence') \
            .write_data(pccf_sat)

        # PCCF Ref Percent Confidence
        obsspace.create_var('MetaData/percentConfidence', dtype=ref_pccf_sat.dtype,
                            fillval=ref_pccf_sat.fill_value) \
            .write_attr('units', '%') \
            .write_attr('long_name', 'Ref Percent Confidence') \
            .write_data(ref_pccf_sat)

        # Azimuth Angle
        obsspace.create_var('MetaData/sensorAzimuthAngle', dtype=bearaz_sat.dtype,
                            fillval=bearaz_sat.fill_value) \
            .write_attr('units', 'degree') \
            .write_attr('long_name', 'Percent Confidence') \
            .write_data(bearaz_sat)

        # Data Provider
        obsspace.create_var('MetaData/dataProviderOrigin', dtype=ogce_sat.dtype,
                            fillval=ogce_sat.fill_value) \
            .write_attr('long_name', 'Identification of Originating Center') \
            .write_data(ogce_sat)

        # Quality: Quality Flags
        obsspace.create_var('MetaData/qfro', dtype=qfro_sat.dtype,
                            fillval=qfro_sat.fill_value) \
            .write_attr('long_name', 'QFRO') \
            .write_data(qfro_sat)

        obsspace.create_var('MetaData/qualityFlags', dtype=qfro2_sat.dtype,
                            fillval=qfro2_sat.fill_value) \
            .write_attr('long_name', 'Quality Flags for QFRO bit5 and bit6') \
            .write_data(qfro2_sat)

        # Quality: Satellite Ascending Flag
        obsspace.create_var('MetaData/satelliteAscendingFlag', dtype=satasc_sat.dtype,
                            fillval=satasc_sat.fill_value) \
            .write_attr('long_name', 'Satellite Ascending Flag') \
            .write_data(satasc_sat)

        # ObsValue: Bending Angle
        obsspace.create_var('ObsValue/bendingAngle', dtype=bnda1_sat.dtype,
                            fillval=bnda1_sat.fill_value) \
            .write_attr('units', 'radians') \
            .write_attr('long_name', 'Bending Angle') \
            .write_data(bnda1_sat)

        # ObsValue: Atmospheric Refractivity
        obsspace.create_var('ObsValue/atmosphericRefractivity', dtype=arfr_sat.dtype,
                            fillval=arfr_sat.fill_value) \
            .write_attr('units', 'N-units') \
            .write_attr('long_name', 'Atmospheric Refractivity') \
            .write_data(arfr_sat)

        # ObsError: Bending Angle
        obsspace.create_var('ObsError/bendingAngle', dtype=bndaoe1_sat.dtype,
                            fillval=bndaoe1_sat.fill_value) \
            .write_attr('units', 'radians') \
            .write_attr('long_name', 'Bending Angle Obs Error') \
            .write_data(bndaoe1_sat)

        # ObsError: Atmospheric Refractivity
        obsspace.create_var('ObsError/atmosphericRefractivity', dtype=arfroe_sat.dtype,
                            fillval=arfroe_sat.fill_value) \
            .write_attr('units', 'N-units') \
            .write_attr('long_name', 'Atmospheric Refractivity Obs Error') \
            .write_data(arfroe_sat)

        # ObsType: Bending Angle
        obsspace.create_var('ObsType/bendingAngle', dtype=bndaot_sat.dtype,
                            fillval=bndaot_sat.fill_value) \
            .write_attr('long_name', 'Bending Angle ObsType') \
            .write_data(bndaot_sat)

        # ObsType: Atmospheric Refractivity
        obsspace.create_var('ObsType/atmosphericRefractivity', dtype=arfrot_sat.dtype,
                            fillval=arfrot_sat.fill_value) \
            .write_attr('long_name', 'Atmospheric Refractivity ObsType') \
            .write_data(arfrot_sat)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Running time for splitting and output IODA for gnssro bufr: \
                 {running_time} seconds")

    logger.debug("All Done!")


if __name__ == '__main__':

    start_time = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str,
                        help='Input JSON configuration', required=True)
    parser.add_argument('-v', '--verbose',
                        help='print debug logging information',
                        action='store_true')
    args = parser.parse_args()

    log_level = 'DEBUG' if args.verbose else 'INFO'
    logger = Logger('bufr2ioda_gnssro.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.debug(f"Total running time: {running_time} seconds")
