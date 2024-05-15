#ifndef BUNDLE_GDAS_UTILS_OBSPROC_RTOFS_RTOFSDATAFILE_H_
#define BUNDLE_GDAS_UTILS_OBSPROC_RTOFS_RTOFSDATAFILE_H_

#include <string>


namespace rtofs
{

class RTOFSOb;

class RTOFSDataFile
{
 public:
    explicit RTOFSDataFile(std::string filename);
    int NumberOfObservations() { return nobs; }
    RTOFSOb & observations() { return * ob; }


 private:
    std::string filename;
    int nobs;
    FILE * f;
    RTOFSOb * ob;

    void read_file();
};    // class RTOFSDataFile

}    // namespace rtofs


#endif    // BUNDLE_GDAS_UTILS_OBSPROC_RTOFS_RTOFSDATAFILE_H_
