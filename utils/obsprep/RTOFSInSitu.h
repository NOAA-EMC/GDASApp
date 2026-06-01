#pragma once

#include <string>
#include <vector>

#include "NetCDFToIodaConverter.h"
#include "rtofs/RTOFSDataFile.h"
#include "rtofs/RTOFSOb.h"
#include "rtofs/util.h"


namespace obsforge
{


namespace rtofs
{

class RTOFSInSitu:
    public NetCDFToIodaConverter
{
 public:
    explicit RTOFSInSitu(
        const eckit::Configuration & fullConfig,
        const eckit::mpi::Comm & comm):
        NetCDFToIodaConverter(fullConfig, comm)
    {}


 protected:
    void ProcessFile(std::string filename);

    rtofs::RTOFSOb * pob;

 private:
    // Read binary file and populate iodaVars
    virtual obsforge::preproc::iodavars::IodaVars
        providerToIodaVars(const std::string filename) = 0;
};  // class RTOFSInSitu


// read the binary file and possibly do additional filtering
// to prepare an rtofs::RTOFSOb to be converted to iodavars object
void
RTOFSInSitu::
    ProcessFile(std::string filename)
{
    oops::Log::info()
        << "Processing RTOFS file "
        << filename
        << std::endl;

    // read the file
    rtofs::RTOFSDataFile RTOFSFile(filename);
    pob = & RTOFSFile.observations();
    rtofs::RTOFSOb & ob = * pob;

    int n = ob.NumberOfObservations();

    // to be used with selection by instrument:
    std::vector<int> tmp_instrument =
        rtofs::find_unique_values(ob.tmp_typ, n);

    std::vector<int> sal_instrument =
        rtofs::find_unique_values(ob.sal_typ, n);
}    // RTOFSInSitu::ProcessFile


}    // namespace rtofs

}  // namespace obsforge
