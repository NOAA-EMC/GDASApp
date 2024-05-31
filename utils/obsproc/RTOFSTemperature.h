#pragma once

#include <string>

#include "RTOFSInSitu.h"


namespace gdasapp
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
    gdasapp::obsproc::iodavars::IodaVars
        providerToIodaVars(const std::string filename) final
    {
        ProcessFile(filename);
        return TemperatureIodaVars();
    }
};  // class RTOFSTemperature


}    // namespace gdasapp
