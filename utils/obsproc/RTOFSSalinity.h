#pragma once


#include <string>

#include "RTOFSInSitu.h"


namespace gdasapp
{


class RTOFSSalinity:
    public rtofs::RTOFSInSitu
{
 public:
    explicit RTOFSSalinity(
        const eckit::Configuration & fullConfig,
        const eckit::mpi::Comm & comm):
        RTOFSInSitu(fullConfig, comm)
    {
        variable_ = "waterSalinity";
    }

    // Read binary file and populate iodaVars
    gdasapp::obsproc::iodavars::IodaVars
        providerToIodaVars(const std::string filename) final
    {
        ProcessFile(filename);
        return SalinityIodaVars();
    }
};  // class RTOFSSalinity


}    // namespace gdasapp
