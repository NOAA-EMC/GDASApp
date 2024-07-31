#pragma once

#include <stdio.h>
#include <string>


namespace gdasapp
{

namespace rtofs
{

class RTOFSOb
{
 public:
    RTOFSOb(int n, int mx_lvl, int vrsn);

    typedef char char12[12];
    typedef char char7[7];

    static int64_t SecondsSinceReferenceTime(char12 time);

    void read(FILE * f);
    int NumberOfObservations() { return n; }
    int TotalNumberOfValues();
    void print(std::string DirectoryName);


    float * btm;        // bottom depth
    float * lat;        // latitude
    float * lon;        // longitude
    int * ls;            // ??
    int * lt;            // array of dimensions, the number of levels
    int * sal_typ;        // ?? salinity type ??
    float * sqc;        // salinity qc
    int * tmp_typ;        // ?? temperature type ??
    float * tqc;        // temperature qc

    // observations per level:
    float ** lvl;        // depth
    float ** sal;        // salinity (PSU)
    float ** sal_err;    // salinity error (std deviation, PSU)
    float ** sprb;        // ?? salinity ... ??
    float ** tmp;        // in situ temperature (C)
    float ** tmp_err;    // in situ temperature error (C)
    float ** tprb;        // ?? temperature ... ??
    float ** clm_sal;    // climatology of salinity
    float ** cssd;        // climatological std deviation for salinity
    float ** clm_tmp;    // climatology of temperature
    float ** ctsd;        // climatological std deviation for temperature
    int ** flg;            // ?? qc flags ??

    char12 * dtg;        // date (Julian, seconds)

 private:
    int n;
    int mx_lvl;
    int vrsn;

    void allocate();
    void allocate2d();
};    // class RTOFSOb

}    // namespace rtofs

}    // namespace gdasapp
