#pragma once

#include <iostream>
#include <netcdf>    // NOLINT (using C API)
#include <regex>
#include <string>
#include <vector>

#include "eckit/config/LocalConfiguration.h"

#include <Eigen/Dense>    // NOLINT

#include "ioda/Group.h"
#include "ioda/ObsGroup.h"

#include "NetCDFToIodaConverter.h"

#include "rtofs/RTOFSDataFile.h"
#include "rtofs/RTOFSOb.h"


namespace gdasapp
{


class RTOFSInSitu:
	public NetCDFToIodaConverter 
{
public:
	explicit RTOFSInSitu(
		const eckit::Configuration & fullConfig, 
		const eckit::mpi::Comm & comm
	):
		NetCDFToIodaConverter(fullConfig, comm)
	{
		variable_ = "temperature";
	}

	// Read binary file and populate iodaVars
	gdasapp::obsproc::iodavars::IodaVars 
	providerToIodaVars(const std::string fileName) final
	{
		oops::Log::info() 
			<< "Processing files provided by RTOFS" 
			<< std::endl
		;

		// Set the int metadata names
		std::vector<std::string> intMetadataNames = {"temperature"};

		// Set the float metadata name
		std::vector<std::string> floatMetadataNames = {};

		// read the file
		oops::Log::info() 
			<< "Processing file "
			<< fileName
			<< std::endl
		;

		rtofs::RTOFSDataFile RTOFSFile(fileName);
		int n = RTOFSFile.NumberOfObservations();
		rtofs::RTOFSOb & ob = RTOFSFile.observations();

		int NumberOfTemperatureValues = 0;
		for (int i = 0;  i < n;  i ++)
			NumberOfTemperatureValues += ob.lt[i];

		gdasapp::obsproc::iodavars::IodaVars iodaVars(
			NumberOfTemperatureValues, 
			floatMetadataNames, 
			intMetadataNames
		);
		iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";

		// debugging output:
		// std::string DataDirectory = "/home/edwardg/da/edwardg/global-workflow/sorc/gdas.cd/build/gdas-utils/test/obsproc/RTOFSdata";
		// ob.print(DataDirectory);

// oops::Log::debug() << "--- iodaVars.location_: " << iodaVars.location_  << std::endl;

		int k = 0;
		for (int i = 0;  i < n;  i ++)
		for (int j = 0;  j < ob.lt[i];  j ++)
		{
			iodaVars.longitude_(k) = ob.lon[i];
			iodaVars.latitude_(k) = ob.lat[i];
			iodaVars.obsVal_(k) = ob.tmp[i][j];
			iodaVars.obsError_(k) = ob.tmp_err[i][j];
			iodaVars.datetime_(k) = ob.dtg[i];
			// iodaVars.preQc_(k) = oneDimFlagsVal[i];
			// iodaVars.intMetadata_.row(k) << -999;

			k ++;
		}

		// basic test for iodaVars.trim
/*
		Eigen::Array<bool, Eigen::Dynamic, 1> mask
			= (iodaVars.obsVal_ > 0.0);
		iodaVars.trim(mask);
*/


		return iodaVars;

	};	// providerToIodaVars

};  // class RTOFSInSitu

}  // namespace gdasapp
