# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
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


def Derive_stationIdentification(said, ptid, stid):

    stid = stid.astype('str')
    for i in range(len(said)):
        stid[i] = str(said[i]).zfill(4)+str(ptid[i]).zfill(4)

    return stid


def Compute_Grid_Location(degrees):

    for i in range(len(degrees)):
        if degrees[i] <= 360 and degrees[i] >= -180:
            degrees[i] = np.deg2rad(degrees[i])
    rad = degrees

    return rad


def Compute_imph(impp, elrc):  # , geodu, imph):

    imph = (impp - elrc).astype(np.float32)

    return imph


def bufr_to_ioda(config, logger):

    subsets = config["subsets"]
    logger.debug(f"Checking subsets = {subsets}")

    # =========================================
    # Get parameters from configuration
    # =========================================
    data_format = config["data_format"]
    data_type = config["data_type"]
    data_description = config["data_description"]
    data_provider = config["data_provider"]
    cycle_type = config["cycle_type"]
    dump_dir = config["dump_directory"]
    ioda_dir = config["ioda_directory"]
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

    logger.info(f"Making QuerySet ...")
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
#    q.add('observationSequenceNum', '*/SEQNUM')
    q.add('geoidUndulation', '*/GEODU')
    q.add('height', '*/ROSEQ3/HEIT')
#    q.add('impactHeightRO_roseq2repl1', '*/ROSEQ1/ROSEQ2{1}/IMPP')
#    q.add('impactHeightRO_roseq2repl3', '*/ROSEQ1/ROSEQ2{3}/IMPP')
    q.add('impactParameterRO_roseq2repl1', '*/ROSEQ1/ROSEQ2{1}/IMPP')
    q.add('impactParameterRO_roseq2repl3', '*/ROSEQ1/ROSEQ2{3}/IMPP')
    q.add('frequency__roseq2repl1', '*/ROSEQ1/ROSEQ2{1}/MEFR')
    q.add('frequency__roseq2repl3', '*/ROSEQ1/ROSEQ2{3}/MEFR')
    q.add('pccf', '*/ROSEQ1/PCCF')
    q.add('percentConfidence', '*/ROSEQ3/PCCF')
    q.add('sensorAzimuthAngle', '*/BEARAZ')

    # Processing Center
    q.add('dataProviderOrigin', '*/OGCE')

    # Quality Information
    q.add('qualityFlags', '*/QFRO')
    q.add('satelliteAscendingFlag', '*/QFRO')

    # ObsValue
    q.add('bendingAngle_roseq2repl1', '*/ROSEQ1/ROSEQ2{1}/BNDA[1]')
    q.add('bendingAngle_roseq2repl3', '*/ROSEQ1/ROSEQ2{3}/BNDA[1]')
    q.add('atmosphericRefractivity', '*/ROSEQ3/ARFR[1]')

    # ObsError
    q.add('obsErrorBendingAngle1', '*/ROSEQ1/ROSEQ2{1}/BNDA[2]')
    q.add('obsErrorBendingAngle3', '*/ROSEQ1/ROSEQ2{3}/BNDA[2]')
    q.add('obsErrorAtmosphericRefractivity', '*/ROSEQ3/ARFR[2]')

    # ObsType
    q.add('obsTypeBendingAngle', '*/SAID')
    q.add('obsTypeAtmosphericRefractivity', '*/SAID')

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for making QuerySet: {running_time} seconds")

    # ==============================================================
    # Open the BUFR file and execute the QuerySet to get ResultSet
    # Use the ResultSet returned to get numpy arrays of the data
    # ==============================================================
    start_time = time.time()

    logger.info(f"Executing QuerySet to get ResultSet ...")
    with bufr.File(DATA_PATH) as f:
        r = f.execute(q)

    logger.info(f" ... Executing QuerySet: get MetaData: basic ...")
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
    stid = r.get('stationIdentification', 'latitude')
    said = r.get('satelliteIdentifier', 'latitude')
    siid = r.get('satelliteInstrument', 'latitude')
    sclf = r.get('satelliteConstellationRO', 'latitude')
    ptid = r.get('satelliteTransmitterId', 'latitude')
    elrc = r.get('earthRadiusCurvature', 'latitude')
#    seqnum = r.get('observationSequenceNum')
    geodu = r.get('geoidUndulation', 'latitude')
    heit = r.get('height', 'height', type='float32').astype(np.float32)
    impp1 = r.get('impactParameterRO_roseq2repl1', 'latitude')
    impp3 = r.get('impactParameterRO_roseq2repl3', 'latitude')
#    imph1 = r.get('impactHeightRO_roseq2repl1', 'latitude')
#    imph3 = r.get('impactHeightRO_roseq2repl3', 'latitude')
    mefr1 = r.get('frequency__roseq2repl1', 'latitude',
                  type='float32').astype(np.float32)
    mefr3 = r.get('frequency__roseq2repl3', 'latitude',
                  type='float32').astype(np.float32)
    pccf = r.get('pccf', 'latitude', type='float32').astype(np.float32)
    ref_pccf = r.get('percentConfidence', 'height')
    bearaz = r.get('sensorAzimuthAngle', 'latitude')

    logger.info(f" ... Executing QuerySet: get MetaData: processing center...")
    # Processing Center
    ogce = r.get('dataProviderOrigin', 'latitude')

    logger.info(f" ... Executing QuerySet: get metadata: data quality \
                information ...")
    # Quality Information
    qfro = r.get('qualityFlags', 'latitude')
    satasc = r.get('satelliteAscendingFlag', 'latitude')

    logger.info(f" ... Executing QuerySet: get ObsValue: Bending Angle ...")
    # ObsValue
    # Bending Angle
    bnda1 = r.get('bendingAngle_roseq2repl1', 'latitude')
    bnda3 = r.get('bendingAngle_roseq2repl3', 'latitude')
    arfr = r.get('atmosphericRefractivity', 'height')

    # ObsError
    # Bending Angle
    bndaoe1 = r.get('obsErrorBendingAngle1', 'latitude')
    bndaoe3 = r.get('obsErrorBendingAngle3', 'latitude')
    arfroe = r.get('obsErrorAtmosphericRefractivity', 'height')

    # ObsType
    # Bending Angle
    bndaot = r.get('obsTypeBendingAngle', 'latitude')
    arfrot = r.get('obsTypeBendingAngle', 'latitude')

    logger.info(f" ... Executing QuerySet: get datatime: observation time ...")
    # DateTime: seconds since Epoch time
    # IODA has no support for numpy datetime arrays dtype=datetime64[s]
    timestamp = r.get_datetime('year', 'month', 'day', 'hour', 'minute',
                               'second', 'latitude').astype(np.int64)

    logger.info(f" ... Executing QuerySet: Done!")

    logger.info(f" ... Executing QuerySet: Check BUFR variable generic \
                dimension and type ...")
    # Check BUFR variable generic dimension and type
    logger.info(f"     clath     shape, type = {clath.shape}, {clath.dtype}")
    logger.info(f"     clonh     shape, type = {clonh.shape}, {clonh.dtype}")
    logger.info(f"     gclath    shape, type = {gclath.shape}, {gclath.dtype}")
    logger.info(f"     gclonh    shape, type = {gclonh.shape}, {gclonh.dtype}")
    logger.info(f"     year      shape, type = {year.shape}, {year.dtype}")
    logger.info(f"     mnth      shape, type = {mnth.shape}, {mnth.dtype}")
    logger.info(f"     days      shape, type = {days.shape}, {days.dtype}")
    logger.info(f"     hour      shape, type = {hour.shape}, {hour.dtype}")
    logger.info(f"     minu      shape, type = {minu.shape}, {minu.dtype}")
    logger.info(f"     seco      shape, type = {seco.shape}, {seco.dtype}")
    logger.info(f"     stid      shape, type = {stid.shape}, {stid.dtype}")
    logger.info(f"     said      shape, type = {said.shape}, {said.dtype}")
    logger.info(f"     siid      shape, type = {siid.shape}, {siid.dtype}")
    logger.info(f"     sclf      shape, type = {sclf.shape}, {sclf.dtype}")
    logger.info(f"     ptid      shape, type = {ptid.shape}, {ptid.dtype}")
    logger.info(f"     elrc      shape, type = {elrc.shape}, {elrc.dtype}")
    logger.info(f"     geodu     shape, type = {geodu.shape}, {geodu.dtype}")
    logger.info(f"     heit      shape, type = {heit.shape}, {heit.dtype}")
    logger.info(f"     impp1     shape, type = {impp1.shape}, {impp1.dtype}")
    logger.info(f"     impp3     shape, type = {impp3.shape}, {impp3.dtype}")
#    logger.info(f"     imph1     shape, {type = {imph1.shape,   imph1.dtype}")
#    logger.info(f"     imph3     shape, {type = {imph3.shape,   imph3.dtype}")
    logger.info(f"     mefr1     shape, type = {mefr1.shape}, {mefr1.dtype}")
    logger.info(f"     mefr3     shape, type = {mefr3.shape}, {mefr3.dtype}")
    logger.info(f"     pccf      shape, type = {pccf.shape}, {pccf.dtype}")
    logger.info(f"     ref_pccf  shape, type = {ref_pccf.shape}, \
                {ref_pccf.dtype}")
    logger.info(f"     bearaz    shape, type = {bearaz.shape}, {bearaz.dtype}")

    logger.info(f"     ogce      shape, type = {ogce.shape}, {ogce.dtype}")

    logger.info(f"     qfro      shape, type = {qfro.shape}, {qfro.dtype}")
    logger.info(f"     satasc    shape, type = {satasc.shape}, {satasc.dtype}")

    logger.info(f"     bnda1     shape, type = {bnda1.shape}, {bnda1.dtype}")
    logger.info(f"     bnda3     shape, type = {bnda3.shape}, {bnda3.dtype}")
    logger.info(f"     arfr      shape, type = {arfr.shape}, {arfr.dtype}")

    logger.info(f"     bndaoe1   shape, type = {bndaoe1.shape}, \
                {bndaoe1.dtype}")
    logger.info(f"     bndaoe3   shape, type = {bndaoe3.shape}, \
                {bndaoe3.dtype}")
    logger.info(f"     arfroe    shape, type = {arfr.shape}, {arfr.dtype}")

    logger.info(f"     bndaot    shape, type = {bndaot.shape}, {bndaot.dtype}")

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for executing QuerySet to get ResultSet: \
                {running_time} seconds")

    # =========================
    # Create derived variables
    # =========================
    start_time = time.time()

    logger.info(f"Creating derived variables - stationIdentification")
    stid = Derive_stationIdentification(said, ptid, stid)

    logger.info(f"     stid shape,type = {stid.shape}, {stid.dtype}")

    logger.info(f"Creating derived variables - Grid Latitude / Longitude ...")
    gclonh = Compute_Grid_Location(gclonh)
    gclath = Compute_Grid_Location(gclath)

    logger.info(f"     gclonh shape,type = {gclonh.shape}, {gclonh.dtype}")
    logger.info(f"     gclath shape,type = {gclath.shape}, {gclath.dtype}")
    logger.info(f"     gclonh min/max = {gclonh.min()}, {gclonh.max()}")
    logger.info(f"     gclath min/max = {gclath.min()}, {gclath.max()}")

    logger.info(f"Creating derived variables - imph ...")
    imph1 = Compute_imph(impp1, elrc)
    imph3 = Compute_imph(impp3, elrc)

    logger.info(f"     imph1 shape,type = {imph1.shape}, {imph1.dtype}")
    logger.info(f"     imph3 shape,type = {imph3.shape}, {imph3.dtype}")
    logger.info(f"     imph1 min/max = {imph1.min()}, {imph1.max()}")
    logger.info(f"     imph3 min/max = {imph3.min()}, {imph3.max()}")

    logger.info(f"Editing some derived variables if SAID is not 44 or 825")
    for i in range(len(said)):
        if (said[i] != 44) or (said[i] != 825):
            bnda1[i] = bnda3[i]
            mefr1[i] = mefr3[i]
            impp1[i] = impp3[i]
            imph1[i] = imph3[i]
            bndaoe1[i] = bndaoe3[i]

    logger.info(f"     new bnda1 shape, type, min/max {bnda1.shape}, \
                {bnda1.dtype}, {bnda1.min()}, {bnda1.max()}")
    logger.info(f"     new mefr1 shape, type, min/max {mefr1.shape}, \
                {mefr1.dtype}, {mefr1.min()}, {mefr1.max()}")
    logger.info(f"     new impp1 shape, type, min/max {impp1.shape}, \
                {impp1.dtype}, {impp1.min()}, {impp1.max()}")
    logger.info(f"     new imph1 shape, type, min/max {imph1.shape}, \
                {imph1.dtype}, {imph1.min()}, {imph1.max()}")
    logger.info(f"     new bndaoe1 shape, type, min/max {bndaoe1.shape}, \
                {bndaoe1.dtype}, {bndaoe1.min()}, {bndaoe1.max()}")

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for creating derived variables: {running_time} \
                seconds")

    # =====================================
    # Create IODA ObsSpace
    # Write IODA output
    # =====================================

    # Find unique satellite identifiers in data to process
    unique_satids = np.unique(said)
    logger.info(f" ... Number of Unique satellite identifiers: \
                {len(unique_satids)}")
    logger.info(f" ... Unique satellite identifiers: {unique_satids}")

    # Create the dimensions
    dims = {'Location': np.arange(0, clath.shape[0])}

    iodafile = f"{cycle_type}.t{hh}z.{data_type}.{data_format}.nc"
    OUTPUT_PATH = os.path.join(ioda_dir, iodafile)
    logger.info(f" ... ... Create OUTPUT file: {OUTPUT_PATH}")

    path, fname = os.path.split(OUTPUT_PATH)
    if path and not os.path.exists(path):
        os.makedirs(path)

    # Create IODA ObsSpace
    obsspace = ioda_ospace.ObsSpace(OUTPUT_PATH, mode='w', dim_dict=dims)

    # Create Global attributes
    logger.info(f" ... ... Create global attributes")
    obsspace.write_attr('data_format', data_format)
    obsspace.write_attr('data_type', data_type)
    obsspace.write_attr('subsets', subsets)
    obsspace.write_attr('cycle_type', cycle_type)
    obsspace.write_attr('cycle_datetime', cycle)
    obsspace.write_attr('dataProviderOrigin', data_provider)
    obsspace.write_attr('description', data_description)
    obsspace.write_attr('converter', os.path.basename(__file__))

    # Create IODA variables
    logger.info(f" ... ... Create variables: name, type, units, & attributes")
    # Longitude
    obsspace.create_var('MetaData/longitude', dtype=clonh.dtype,
                        fillval=clonh.fill_value) \
        .write_attr('units', 'degrees_east') \
        .write_attr('valid_range', np.array([-180, 180], dtype=np.float32)) \
        .write_attr('long_name', 'Longitude') \
        .write_data(clonh)

    # Latitude
    obsspace.create_var('MetaData/latitude', dtype=clath.dtype,
                        fillval=clath.fill_value) \
        .write_attr('units', 'degrees_north') \
        .write_attr('valid_range', np.array([-90, 90], dtype=np.float32)) \
        .write_attr('long_name', 'Latitude') \
        .write_data(clath)

    # Grid Longitude
    obsspace.create_var('MetaData/gridLongitude', dtype=gclonh.dtype,
                        fillval=gclonh.fill_value) \
        .write_attr('units', 'radians') \
        .write_attr('valid_range', np.array([-3.14159265, 3.14159265],
                    dtype=np.float32)) \
        .write_attr('long_name', 'Grid Longitude') \
        .write_data(gclonh)

    # Grid Latitude
    obsspace.create_var('MetaData/gridLatitude', dtype=gclath.dtype,
                        fillval=gclath.fill_value) \
        .write_attr('units', 'radians') \
        .write_attr('valid_range', np.array([-1.570796325, 1.570796325],
                    dtype=np.float32)) \
        .write_attr('long_name', 'Grid Latitude') \
        .write_data(gclath)

    # Datetime
    obsspace.create_var('MetaData/dateTime', dtype=np.int64,
                        fillval=timestamp.fill_value) \
        .write_attr('units', 'seconds since 1970-01-01T00:00:00Z') \
        .write_attr('long_name', 'Datetime') \
        .write_data(timestamp)

    # Station Identification
    obsspace.create_var('MetaData/stationIdentification', dtype=stid.dtype,
                        fillval=stid.fill_value) \
        .write_attr('long_name', 'Station Identification') \
        .write_data(stid)

    # Satellite Identifier
    obsspace.create_var('MetaData/satelliteIdentifier', dtype=said.dtype,
                        fillval=said.fill_value) \
        .write_attr('long_name', 'Satellite Identifier') \
        .write_data(said)

    # Satellite Instrument
    obsspace.create_var('MetaData/satelliteInstrument', dtype=siid.dtype,
                        fillval=siid.fill_value) \
        .write_attr('long_name', 'Satellite Instrument') \
        .write_data(siid)

    # Satellite Constellation RO
    obsspace.create_var('MetaData/satelliteConstellationRO', dtype=sclf.dtype,
                        fillval=sclf.fill_value) \
        .write_attr('long_name', 'Satellite Constellation RO') \
        .write_data(sclf)

    # Satellite Transmitter ID
    obsspace.create_var('MetaData/satelliteTransmitterId', dtype=ptid.dtype,
                        fillval=ptid.fill_value) \
        .write_attr('long_name', 'Satellite Transmitter Id') \
        .write_data(ptid)

    # Earth Radius Curvature
    obsspace.create_var('MetaData/earthRadiusCurvature', dtype=elrc.dtype,
                        fillval=elrc.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Earth Radius of Curvature') \
        .write_data(elrc)

    # Geoid Undulation
    obsspace.create_var('MetaData/geoidUndulation', dtype=geodu.dtype,
                        fillval=geodu.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Geoid Undulation') \
        .write_data(geodu)

    # Height
    obsspace.create_var('MetaData/height', dtype=heit.dtype,
                        fillval=heit.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Height') \
        .write_data(heit)

    # Impact Parameter RO
    obsspace.create_var('MetaData/impactParameterRO', dtype=impp1.dtype,
                        fillval=impp1.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Impact Parameter RO') \
        .write_data(impp1)

    # Impact Height RO
    obsspace.create_var('MetaData/impactHeightRO', dtype=imph1.dtype,
                        fillval=imph1.fill_value) \
        .write_attr('units', 'm') \
        .write_attr('long_name', 'Impact Height RO') \
        .write_data(imph1)

    # Impact Height RO
    obsspace.create_var('MetaData/frequency', dtype=mefr1.dtype,
                        fillval=mefr1.fill_value) \
        .write_attr('units', 'Hz') \
        .write_attr('long_name', 'Frequency') \
        .write_data(mefr1)

    # PCCF Percent Confidence
    obsspace.create_var('MetaData/pccf', dtype=pccf.dtype,
                        fillval=pccf.fill_value) \
        .write_attr('units', '%') \
        .write_attr('long_name', 'Percent Confidence') \
        .write_data(pccf)

    # PCCF Ref Percent Confidence
    obsspace.create_var('MetaData/percentConfidence', dtype=ref_pccf.dtype,
                        fillval=ref_pccf.fill_value) \
        .write_attr('units', '%') \
        .write_attr('long_name', 'Ref Percent Confidence') \
        .write_data(ref_pccf)

    # Azimuth Angle
    obsspace.create_var('MetaData/sensorAzimuthAngle', dtype=bearaz.dtype,
                        fillval=bearaz.fill_value) \
        .write_attr('units', 'degree') \
        .write_attr('long_name', 'Percent Confidence') \
        .write_data(bearaz)

    # Data Provider
    obsspace.create_var('MetaData/dataProviderOrigin', dtype=ogce.dtype,
                        fillval=ogce.fill_value) \
        .write_attr('long_name', 'Identification of Originating Center') \
        .write_data(ogce)

    # Quality: Quality Flags
    obsspace.create_var('MetaData/qualityFlags', dtype=qfro.dtype,
                        fillval=qfro.fill_value) \
        .write_attr('long_name', 'Quality Flags') \
        .write_data(qfro)

    # Quality: Satellite Ascending Flag
    obsspace.create_var('MetaData/satelliteAscendingFlag', dtype=satasc.dtype,
                        fillval=satasc.fill_value) \
        .write_attr('long_name', 'Satellite Ascending Flag') \
        .write_data(satasc)

    # ObsValue: Bending Angle
    obsspace.create_var('ObsValue/bendingAngle', dtype=bnda1.dtype,
                        fillval=bnda1.fill_value) \
        .write_attr('units', 'radians') \
        .write_attr('long_name', 'Bending Angle') \
        .write_data(bnda1)

    # ObsValue: Atmospheric Refractivity
    obsspace.create_var('ObsValue/atmosphericRefractivity', dtype=arfr.dtype,
                        fillval=arfr.fill_value) \
        .write_attr('units', 'N-units') \
        .write_attr('long_name', 'Atmospheric Refractivity ObsError') \
        .write_data(arfr)

    # ObsError: Bending Angle
    obsspace.create_var('ObsError/bendingAngle', dtype=bndaoe1.dtype,
                        fillval=bndaoe1.fill_value) \
        .write_attr('units', 'radians') \
        .write_attr('long_name', 'Bending Angle Obs Error') \
        .write_data(bndaoe1)

    # ObsError: Atmospheric Refractivity
    obsspace.create_var('ObsError/atmosphericRefractivity', dtype=arfroe.dtype,
                        fillval=arfroe.fill_value) \
        .write_attr('units', 'N-units') \
        .write_attr('long_name', 'Atmospheric Refractivity ObsError') \
        .write_data(arfroe)

    # ObsType: Bending Angle
    obsspace.create_var('ObsType/BendingAngle', dtype=bndaot.dtype,
                        fillval=bndaot.fill_value) \
        .write_attr('long_name', 'Bending Angle ObsType') \
        .write_data(bndaot)

    # ObsType: Atmospheric Refractivity
    obsspace.create_var('ObsType/atmosphericRefractivity', dtype=arfrot.dtype,
                        fillval=arfrot.fill_value) \
        .write_attr('long_name', 'Atmospheric Refractivity ObsType') \
        .write_data(arfrot)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Running time for splitting and output IODA for gpsro bufr: \
                {running_time} seconds")

    logger.info("All Done!")


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
    logger = Logger('bufr2ioda_acft_profiles_prepbufr.py', level=log_level,
                    colored_log=True)

    with open(args.config, "r") as json_file:
        config = json.load(json_file)

    bufr_to_ioda(config, logger)

    end_time = time.time()
    running_time = end_time - start_time
    logger.info(f"Total running time: {running_time} seconds")
