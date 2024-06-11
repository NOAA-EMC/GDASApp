#pragma once

#include <stdio.h>
#include <string>

#include "RTOFSOb.h"


namespace gdasapp
{
namespace rtofs
{

class RTOFSDataFile
{
 public:
    explicit RTOFSDataFile(std::string filename);
    RTOFSOb & observations() { return * ob; }

 private:
    FILE * f;
    RTOFSOb * ob;

    void read_file();
};    // class RTOFSDataFile

}    // namespace rtofs

}    // namespace gdasapp
