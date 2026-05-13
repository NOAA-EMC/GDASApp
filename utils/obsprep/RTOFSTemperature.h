#pragma once

#include <string>
#include <vector>

#include "rtofs/RTOFSOb.h"
#include "RTOFSInSitu.h"


namespace obsforge
{


class RTOFSTemperature:
    public rtofs::RTOFSInSitu
{
 public:
    explicit RTOFSTemperature(
        const eckit::Configuration & fullConfig,
        const eckit::mpi::Comm & comm):
        RTOFSInSitu(fullConfig, comm)
    {
        variable_ = "waterTemperature";
    }

    // Read binary file and populate iodaVars
    obsforge::preproc::iodavars::IodaVars
        providerToIodaVars(const std::string filename) final;
};  // class RTOFSTemperature



obsforge::preproc::iodavars::IodaVars
RTOFSTemperature::
    providerToIodaVars(const std::string filename)
{
    ProcessFile(filename);

    // Set the int metadata names
    std::vector<std::string> intMetadataNames = {"tmp_typ"};

    // Set the float metadata name
    std::vector<std::string> floatMetadataNames = {"level"};
    rtofs::RTOFSOb & ob = * pob;

    obsforge::preproc::iodavars::IodaVars iodaVars(
        ob.TotalNumberOfValues(),
        1,
        floatMetadataNames,
        intMetadataNames);

    iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";
    iodaVars.niMetadata_ = 1;
    iodaVars.nfMetadata_ = 1;

    int n = ob.NumberOfObservations();

    int k = 0;
    for (int i = 0;  i < n;  i ++)
    {
        int64_t date = rtofs::RTOFSOb::SecondsSinceReferenceTime(ob.dtg[i]);

        for (int j = 0;  j < ob.lt[i];  j ++)
        {
            iodaVars.longitude_(k) = ob.lon[i];
            iodaVars.latitude_(k) = ob.lat[i];
            iodaVars.obsVal_(k) = ob.tmp[i][j];
            iodaVars.obsError_(k) = ob.tmp_err[i][j];
            iodaVars.datetime_(k) = date;
            iodaVars.preQc_(k) = ob.flg[i][j];
            iodaVars.intMetadata_.row(k) << ob.tmp_typ[i];
            iodaVars.floatMetadata_.row(k) << ob.lvl[i][j];

            k++;
        }
    }

    return iodaVars;
};  // class RTOFSTemperature


}    // namespace obsforge
