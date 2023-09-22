# (C) Copyright 2023 NOAA/NWS/NCEP/EMC
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.

import sys
sys.path.append('/work2/noaa/da/pkumar/ioda-bundle_20230705/build/lib/')
sys.path.append('/work2/noaa/da/pkumar/ioda-bundle_20230705/build/lib/pyiodaconv/')
sys.path.append('/work2/noaa/da/pkumar/ioda-bundle_20230705/build/lib/python3.9/pyioda/')

#sys.path.append('/work2/noaa/da/pkumar/ioda-bundle/build/lib/')
#sys.path.append('/work2/noaa/da/pkumar/ioda-bundle/build/lib/pyiodaconv/')
#sys.path.append('/work2/noaa/da/pkumar/ioda-bundle/build/lib/python3.9/pyioda/')

#import pyiodaconv.ioda_conv_engines as iconv
#import pyiodaconv.ioda_conv_ncio as iconio
#from pyiodaconv import bufr

import numpy as np
import bufr
import ioda
import calendar
import time
import math
import ioda_obs_space as ioda_ospace

DATA_PATH = '/work2/noaa/da/pkumar/IODA_CONVR_Python/testinput/ADPUPA.prepbufr'
OUTPUT_PATH = './testrun/prepbufr_adpupa_api_v1.nc'

def test_bufr_to_ioda():

    # Make the QuerySet for all the data we want
    q = bufr.QuerySet()

    # MetaData
    q.add('prepbufrDataLevelCategory', '*/PRSLEVEL/CAT')
    q.add('latitude', '*/PRSLEVEL/DRFTINFO/YDR')
    q.add('longitude', '*/PRSLEVEL/DRFTINFO/XDR')
    q.add('stationIdentification', '*/SID')
    q.add('stationElevation', '*/ELV')
    q.add('timeOffset', '*/PRSLEVEL/DRFTINFO/HRDR')
    q.add('temperatureEventCode','*/PRSLEVEL/T___INFO/T__EVENT{1}/TPC')
    q.add('pressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')

    # ObsValue
    q.add('stationPressure', '*/PRSLEVEL/P___INFO/P__EVENT{1}/POB')
    q.add('airTemperature', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TOB')
    #q.add('virtualTemperature', '*/PRSLEVEL/T___INFO/TVO')
    q.add('specificHumidity', '*/PRSLEVEL/Q___INFO/Q__EVENT{1}/QOB')
    q.add('windEastward', '*/PRSLEVEL/W___INFO/W__EVENT{1}/UOB')
    q.add('windNorthward', '*/PRSLEVEL/W___INFO/W__EVENT{1}/VOB')
    q.add('heightOfObservation', '*/PRSLEVEL/Z___INFO/Z__EVENT{1}/ZOB')

    # QualityMark
    q.add('pressureQM', '*/PRSLEVEL/P___INFO/P__EVENT{1}/PQM')
    q.add('airTemperatureQM', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
    q.add('virtualTemperatureQM', '*/PRSLEVEL/T___INFO/T__EVENT{1}/TQM')
    q.add('specificHumidityQM', '*/PRSLEVEL/Q___INFO/Q__EVENT{1}/QQM')
    q.add('windEastwardQM', '*/PRSLEVEL/W___INFO/W__EVENT{1}/WQM')
    q.add('windNorthwardQM', '*/PRSLEVEL/W___INFO/W__EVENT{1}/WQM')
 
    # Open the BUFR file and execute the QuerySet
    with bufr.File(DATA_PATH) as f:
        r = f.execute(q)

    # Use the ResultSet returned to get numpy arrays of the data
    # MetaData
    cat = r.get('prepbufrDataLevelCategory', 'prepbufrDataLevelCategory')
    lat = r.get('latitude', 'prepbufrDataLevelCategory')
    lon = r.get('longitude', 'prepbufrDataLevelCategory')
    lon[lon>180] -= 360  # Convert Longitude from [0,360] to [-180,180]
    sid = r.get('stationIdentification', 'prepbufrDataLevelCategory')
    elv = r.get('stationElevation', 'prepbufrDataLevelCategory')
    tpc = r.get('temperatureEventCode', 'prepbufrDataLevelCategory')
    pob = r.get('pressure', 'prepbufrDataLevelCategory')
    pob *= 100

    print('lat shape = ', lat.shape)
    print('lon shape = ', lon.shape)

    # Time variable
    hrdr = r.get('timeOffset', 'prepbufrDataLevelCategory')
    print("cycleTimeSinceEpoch")
    cycleTimeSinceEpoch = np.int64(calendar.timegm(time.strptime('2021 08 01 00 00 00', '%Y %m %d %H %M %S')))
    hrdr = np.int64(hrdr*3600)
    hrdr += cycleTimeSinceEpoch

    # releaseTime
    #ulan = np.repeat(hrdr[:,0], hrdr.shape[1])
    #ulan = np.repeat(hrdr[:,0], hrdr.shape[1])
    #ulan = ulan.reshape(hrdr.shape)
    print('hrdr', hrdr)

    #exit ()
    # ObsValue
    pob_ps   = np.full(pob.shape[0], pob.fill_value) # Extract stationPressure from pressure, which belongs to CAT=1
    pob_ps   = np.where(cat == 0, pob, pob_ps)  
    tob = r.get('airTemperature', 'prepbufrDataLevelCategory')
    tob += 273.15
    tsen = np.full(tob.shape[0], tob.fill_value) # Extract sensible temperature from tob, which belongs to TPC=1
    tsen = np.where(tpc == 1, tob, tsen)
    tvo   = np.full(tob.shape[0], tob.fill_value) # Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
    tvo   = np.where(((tpc <= 8) & (tpc > 1)), tob, tvo)
    qob = r.get('specificHumidity', 'prepbufrDataLevelCategory', type='float')
    qob *= 1.0e-6
    uob = r.get('windEastward', 'prepbufrDataLevelCategory')
    vob = r.get('windNorthward', 'prepbufrDataLevelCategory')
    zob = r.get('heightOfObservation', 'prepbufrDataLevelCategory')

    # QualityMark
    pobqm = r.get('pressureQM', 'prepbufrDataLevelCategory')
    pob_psqm = np.full(pobqm.shape[0], pobqm.fill_value) # Extract stationPressureQM from pressureQM
    pob_psqm   = np.where(cat == 0, pobqm, pob_psqm)
    tobqm = r.get('airTemperatureQM', 'prepbufrDataLevelCategory')
    tsenqm = np.full(tobqm.shape[0], tobqm.fill_value) # Extract airTemperature from tobqm, which belongs to TPC=1
    tsenqm = np.where(tpc == 1, tobqm, tsenqm)
    tvoqm   = np.full(tobqm.shape[0], tobqm.fill_value) # Extract virtual temperature from tob, which belongs to TPC <= 8 and TPC>1
    tvoqm   = np.where(((tpc <= 8) & (tpc > 1)), tobqm, tvoqm)
    qobqm = r.get('specificHumidityQM', 'prepbufrDataLevelCategory')
    uobqm = r.get('windEastwardQM', 'prepbufrDataLevelCategory')
    vobqm = r.get('windNorthwardQM', 'prepbufrDataLevelCategory')

    # Write the data to an IODA file
    g = ioda.Engines.HH.createFile(name=OUTPUT_PATH,
                                   mode=ioda.Engines.BackendCreateModes.Truncate_If_Exists)

    # Create the dimensions
    print("Create dimensions")
    num_locs = lat.shape[0]

    dim_location = g.vars.create('Location', ioda.Types.int32, [num_locs])
    dim_location.scales.setIsScale('Location')

    print("creation parameters, set fill value and compress")
    pfloat = ioda.VariableCreationParameters()
    pdouble = ioda.VariableCreationParameters()
    pint = ioda.VariableCreationParameters()
    pint64 = ioda.VariableCreationParameters()

    pfloat.setFillValue.float(lat.fill_value)
    pdouble.setFillValue.double(qob.fill_value)
    pint.setFillValue.int(elv.fill_value)
    pint64.setFillValue.int64(hrdr.fill_value)

    pfloat.compressWithGZIP()
    pdouble.compressWithGZIP()
    pint.compressWithGZIP()
    pint64.compressWithGZIP()

    # Create the variables
    print("Create MetaData group variables")
    prepbufrdatalevelcategory = g.vars.create('MetaData/prepbufrDataLevelCategory', ioda.Types.int,  scales=[dim_location], params=pint)
    prepbufrdatalevelcategory.atts.create('units', ioda.Types.str).writeVector.str([''])
    prepbufrdatalevelcategory.atts.create('long_name', ioda.Types.str).writeVector.str(['Prepbufr Data Level Category'])

    latitude = g.vars.create('MetaData/latitude', ioda.Types.float,  scales=[dim_location], params=pfloat)
    latitude.atts.create('valid_range', ioda.Types.float, [2]).writeVector.float([-90, 90])
    latitude.atts.create('units', ioda.Types.str).writeVector.str(['degree_north'])
    latitude.atts.create('long_name', ioda.Types.str).writeVector.str(['Latitude'])

    longitude = g.vars.create('MetaData/longitude', ioda.Types.float, scales=[dim_location], params=pfloat)
    longitude.atts.create('valid_range', ioda.Types.float, [2]).writeVector.float([-180, 180])
    longitude.atts.create('units', ioda.Types.str).writeVector.str(['degree_east'])
    longitude.atts.create('long_name', ioda.Types.str).writeVector.str(['Longitude'])

    stationidentification = g.vars.create('MetaData/stationIdentification', ioda.Types.str, scales=[dim_location])
    stationidentification.atts.create('long_name', ioda.Types.str).writeVector.str(['Station Identification'])

    stationelevation = g.vars.create('MetaData/stationElevation', ioda.Types.float, scales=[dim_location], params=pfloat)
    stationelevation.atts.create('units', ioda.Types.str).writeVector.str(['m'])
    stationelevation.atts.create('long_name', ioda.Types.str).writeVector.str(['Station Elevation'])

    datetime = g.vars.create('MetaData/dateTime',  ioda.Types.int64,  scales=[dim_location], params=pint64)
    datetime.atts.create('units', ioda.Types.str).writeVector.str(['seconds since 1970-01-01T00:00:00Z'])

    #releasetime = g.vars.create('MetaData/releaseTime',  ioda.Types.int64,  scales=[dim_location], params=pint64)
    #releasetime.atts.create('units', ioda.Types.str).writeVector.str(['seconds since 1970-01-01T00:00:00Z'])

    temperatureeventcode = g.vars.create('MetaData/temperatureEventCode', ioda.Types.int, scales=[dim_location], params=pint)
    temperatureeventcode.atts.create('units', ioda.Types.str).writeVector.str(['1'])
    temperatureeventcode.atts.create('long_name', ioda.Types.str).writeVector.str(['temperatureEventCode'])

    pressure = g.vars.create('MetaData/pressure', ioda.Types.float, scales=[dim_location], params=pfloat)
    pressure.atts.create('units', ioda.Types.str).writeVector.str(['Pa'])
    pressure.atts.create('long_name', ioda.Types.str).writeVector.str(['Pressure'])

    print("Create ObsValue group variables")
    stationpressure = g.vars.create('ObsValue/stationPressure', ioda.Types.float, scales=[dim_location], params=pfloat)
    stationpressure.atts.create('units', ioda.Types.str).writeVector.str(['Pa'])
    stationpressure.atts.create('long_name', ioda.Types.str).writeVector.str(['Station Pressure'])

    airtemperature = g.vars.create('ObsValue/airTemperature', ioda.Types.float, scales=[dim_location], params=pfloat)
    airtemperature.atts.create('units', ioda.Types.str).writeVector.str(['K'])
    airtemperature.atts.create('long_name', ioda.Types.str).writeVector.str(['Temperature'])

    virtualtemperature = g.vars.create('ObsValue/virtualTemperature', ioda.Types.float, scales=[dim_location], params=pfloat)
    virtualtemperature.atts.create('units', ioda.Types.str).writeVector.str(['K'])
    virtualtemperature.atts.create('long_name', ioda.Types.str).writeVector.str(['Virtual Temperature'])

    specifichumidity = g.vars.create('ObsValue/specificHumidity', ioda.Types.float, scales=[dim_location], params=pfloat)
    specifichumidity.atts.create('units', ioda.Types.str).writeVector.str(['kg kg-1'])
    specifichumidity.atts.create('long_name', ioda.Types.str).writeVector.str(['Specific Humidity'])

    windeastward = g.vars.create('ObsValue/windEastward', ioda.Types.float, scales=[dim_location], params=pfloat)
    windeastward.atts.create('units', ioda.Types.str).writeVector.str(['m s-1'])
    windeastward.atts.create('long_name', ioda.Types.str).writeVector.str(['Eastward Wind'])

    windnorthward = g.vars.create('ObsValue/windNorthward', ioda.Types.float, scales=[dim_location], params=pfloat)
    windnorthward.atts.create('units', ioda.Types.str).writeVector.str(['m s-1'])
    windnorthward.atts.create('long_name', ioda.Types.str).writeVector.str(['Northward Wind'])

    heightofobservation = g.vars.create('ObsValue/heightOfObservation', ioda.Types.int, scales=[dim_location], params=pint)
    heightofobservation.atts.create('units', ioda.Types.str).writeVector.str(['m'])
    heightofobservation.atts.create('long_name', ioda.Types.str).writeVector.str(['Height of Observation'])

    print("Create QualityMarker group variables")
    pressureqm = g.vars.create('QualityMarker/pressure', ioda.Types.int, scales=[dim_location], params=pint)
    pressureqm.atts.create('units', ioda.Types.str).writeVector.str(['1'])
    pressureqm.atts.create('long_name', ioda.Types.str).writeVector.str(['Pressure Quality Marker'])

    stationpressureqm = g.vars.create('QualityMarker/stationPressure', ioda.Types.int, scales=[dim_location], params=pint)
    stationpressureqm.atts.create('units', ioda.Types.str).writeVector.str(['1'])
    stationpressureqm.atts.create('long_name', ioda.Types.str).writeVector.str(['Station Pressure Quality Marker'])

    airtemperatureqm = g.vars.create('QualityMarker/airTemperature', ioda.Types.int, scales=[dim_location], params=pint)
    airtemperatureqm.atts.create('units', ioda.Types.str).writeVector.str(['1'])
    airtemperatureqm.atts.create('long_name', ioda.Types.str).writeVector.str(['Air Temperature Quality Marker'])

    virtualtemperatureqm = g.vars.create('QualityMarker/virtualTemperature', ioda.Types.int, scales=[dim_location], params=pint)
    virtualtemperatureqm.atts.create('units', ioda.Types.str).writeVector.str(['1'])
    virtualtemperatureqm.atts.create('long_name', ioda.Types.str).writeVector.str(['Virtual Temperature Quality Marker'])

    specifichumidityqm = g.vars.create('QualityMarker/specificHumidity', ioda.Types.int, scales=[dim_location], params=pint)
    specifichumidityqm.atts.create('units', ioda.Types.str).writeVector.str(['1'])
    specifichumidityqm.atts.create('long_name', ioda.Types.str).writeVector.str(['Specific Humidity Quality Marker'])

    windnorthwardqm = g.vars.create('QualityMarker/windNorthward', ioda.Types.int, scales=[dim_location], params=pint)
    windnorthwardqm.atts.create('units', ioda.Types.str).writeVector.str(['1'])
    windnorthwardqm.atts.create('long_name', ioda.Types.str).writeVector.str(['Northward Quality Marker'])

    windeastwardqm = g.vars.create('QualityMarker/windEastward', ioda.Types.int, scales=[dim_location], params=pint)
    windeastwardqm.atts.create('units', ioda.Types.str).writeVector.str(['1'])
    windeastwardqm.atts.create('long_name', ioda.Types.str).writeVector.str(['Eastward Wind Quality Marker'])

    # Write data to the variables
    print("Write data to variables")
    prepbufrdatalevelcategory.writeNPArray.int(cat.flatten())
    latitude.writeNPArray.float(lat.flatten())
    longitude.writeNPArray.float(lon.flatten())
    stationidentification.writeVector.str(sid.flatten())
    stationelevation.writeNPArray.float(elv.flatten())
    datetime.writeNPArray.int64(hrdr.flatten())
    #releasetime.writeNPArray.int64(ulan.flatten())
    temperatureeventcode.writeNPArray.int(tpc.flatten())
    pressure.writeNPArray.float(pob.flatten())

    stationpressure.writeNPArray.float(pob_ps.flatten())
    airtemperature.writeNPArray.float(tsen.flatten())
    virtualtemperature.writeNPArray.float(tvo.flatten())
    specifichumidity.writeNPArray.float(qob.flatten())
    windeastward.writeNPArray.float(uob.flatten())
    windnorthward.writeNPArray.float(vob.flatten())
    heightofobservation.writeNPArray.int(zob.flatten())

    pressureqm.writeNPArray.int(pobqm.flatten())
    stationpressureqm.writeNPArray.int(pob_psqm.flatten())
    airtemperatureqm.writeNPArray.int(tsenqm.flatten())
    virtualtemperatureqm.writeNPArray.int(tvoqm.flatten())
    specifichumidityqm.writeNPArray.int(qobqm.flatten())
    windeastwardqm.writeNPArray.int(uobqm.flatten())
    windnorthwardqm.writeNPArray.int(vobqm.flatten())

if __name__ == '__main__':
    test_bufr_to_ioda()
