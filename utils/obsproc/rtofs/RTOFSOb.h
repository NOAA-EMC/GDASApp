#ifndef BUNDLE_GDAS_UTILS_OBSPROC_RTOFS_RTOFSOB_H_
#define BUNDLE_GDAS_UTILS_OBSPROC_RTOFS_RTOFSOB_H_


#include <stdio.h>
#include <ctime>

#include <string>
using std::string;

namespace rtofs
{


class RTOFSOb
{
 public:
    RTOFSOb(int n, int mx_lvl, int vrsn);

    void read(FILE * f);
    int NumberOfObservations() { return n; }
    void print(std::string DirectoryName);


    float * btm;
    float * lat;
    float * lon;
    int * ls;
    int * lt;
    int * sal_typ;
    float * sqc;
    int * tmp_typ;
    float * tqc;

    float ** lvl;
    float ** sal;
    float ** sal_err;
    float ** sprb;
    float ** tmp;
    float ** tmp_err;
    float ** tprb;
    float ** clm_sal;
    float ** cssd;
    float ** clm_tmp;
    float ** ctsd;
    int ** flg;

    std::time_t * dtg;

 private:
    int n;
    int mx_lvl;
    int vrsn;

    void allocate();
    void allocate2d();
};    // class RTOFSOb


}    // namespace rtofs

#endif  // BUNDLE_GDAS_UTILS_OBSPROC_RTOFS_RTOFSOB_H_
