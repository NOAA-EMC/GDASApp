// NOLINT
#include <iostream>
#include <fstream>  // NOLINT

#include "rtofs/RTOFSOb.h"
#include "rtofs/util.h"
#include "oops/util/dateFunctions.h"

using std::cerr;
using std::endl;
using std::cout;
using std::ofstream;
namespace obsforge
{
namespace rtofs
{



int64_t
RTOFSOb::
    SecondsSinceReferenceTime(rtofs::RTOFSOb::char12 time)
{
    // parse the date
    std::string s(time);
    int year = std::stoi(s.substr(0, 4));
    int month = std::stoi(s.substr(4, 2));
    int day = std::stoi(s.substr(6, 2));
    int hour = std::stoi(s.substr(8, 2));
    int minute = std::stoi(s.substr(10, 2));
    int second = 0;

    uint64_t julianDate =
        util::datefunctions::dateToJulian(year, month, day);

    // 2440588 = Julian date for January 1, 1970.
    int daysSinceEpoch = julianDate - 2440588;
    int secondsOffset = util::datefunctions::hmsToSeconds(hour, minute, second);
    return static_cast<int64_t>(daysSinceEpoch * 86400.0f) + secondsOffset;
}    // SecondsSinceReferenceTime



// the variables marked "skipped" are arrays which are present
// in the binary file, but were skipped by the fortran code
// that was reading the files.

RTOFSOb::
    RTOFSOb(int n, int mx_lvl, int vrsn):
        n(n),
        mx_lvl(mx_lvl),
        vrsn(vrsn)
{
    allocate();
}


int
RTOFSOb::
    TotalNumberOfValues()
{
    int NumberOfValues = 0;
    for (int i = 0;  i < n;  i ++)
        NumberOfValues += lt[i];
    return NumberOfValues;
}



void
RTOFSOb::
    allocate()
{
    dtg = new char12[n];

    lat = new float[n];
    lon = new float[n];
    btm = new float[n];
    ls = new int[n];
    lt = new int[n];
    sal_typ = new int[n];
    sqc = new float[n];
    tmp_typ = new int[n];
    tqc = new float[n];

    lvl = new float * [n];
    sal = new float * [n];
    sal_err = new float * [n];
    sprb = new float * [n];
    tmp = new float * [n];
    tmp_err = new float * [n];
    clm_sal = new float * [n];    // skipped
    tprb = new float * [n];
    cssd = new float * [n];
    clm_tmp = new float * [n];    // skipped
    ctsd = new float * [n];
    flg = new int * [n];
}


void
RTOFSOb::
    allocate2d()
{
    for (int i = 0;  i < n;  i ++)
    {
        int k = lt[i];

        lvl[i] = new float[k];
        sal[i] = new float[k];
        sal_err[i] = new float[k];
        sprb[i] = new float[k];
        tmp[i] = new float[k];
        tmp_err[i] = new float[k];
        tprb[i] = new float[k];
        clm_sal[i] = new float[k];
        cssd[i] = new float[k];
        clm_tmp[i] = new float[k];
        ctsd[i] = new float[k];
        flg[i] = new int[k];
    }
}



void
RTOFSOb::
    read(FILE * f)
{
    read_float_array(f, btm, n);
    read_float_array(f, lat, n);
    read_float_array(f, lon, n);
    read_int_array(f, ls, n);
    read_int_array(f, lt, n);
    read_int_array(f, sal_typ, n);
    read_float_array(f, sqc, n);
    read_int_array(f, tmp_typ, n);
    read_float_array(f, tqc, n);

    allocate2d();

    for (int i = 0;  i < n;  i ++)
    {
        int k = lt[i];

        read_float_array(f, lvl[i], k);
        read_float_array(f, sal[i], k);
        read_float_array(f, sal_err[i], k);
        read_float_array(f, sprb[i], k);
        read_float_array(f, tmp[i], k);
        read_float_array(f, tmp_err[i], k);
        read_float_array(f, tprb[i], k);
        read_float_array(f, clm_sal[i], k);
        read_float_array(f, cssd[i], k);
        read_float_array(f, clm_tmp[i], k);
        read_float_array(f, ctsd[i], k);
        read_int_array(f, flg[i], k);
    }
}


// helpful function to dump ascii files that can be visualized
// with python scripts
void
RTOFSOb::
    print(std::string DirectoryName)
{
    if (!file_exists(DirectoryName))
    {
        cerr << "Directory " << DirectoryName << "doesn't exist" << endl;
        exit(1);
    }
    print_float_array(DirectoryName + "/latitude", lat, n);
    print_float_array(DirectoryName + "/longitude", lon, n);
    print_float_array(DirectoryName + "/btm", btm, n);
    print_float_array(DirectoryName + "/tqc", tqc, n);
    print_float_array(DirectoryName + "/sqc", sqc, n);
    print_int_array(DirectoryName + "/lt", lt, n);
    print_int_array(DirectoryName + "/ls", ls, n);
    print_int_array(DirectoryName + "/sal_typ", sal_typ, n);
    print_int_array(DirectoryName + "/tmp_typ", tmp_typ, n);

    print_2d_array<float>(DirectoryName + "/tmp", tmp, n, lt);
    print_2d_array<float>(DirectoryName + "/sal", sal, n, lt);
    print_2d_array<float>(DirectoryName + "/lvl", lvl, n, lt);
    print_2d_array<float>(DirectoryName + "/cssd", cssd, n, lt);
    print_2d_array<float>(DirectoryName + "/ctsd", ctsd, n, lt);
    print_2d_array<float>(DirectoryName + "/tprb", tprb, n, lt);
    print_2d_array<float>(DirectoryName + "/sprb", sprb, n, lt);
    print_2d_array<float>(DirectoryName + "/clm_tmp", clm_tmp, n, lt);

    print_level(DirectoryName + "/tmp0", tmp, n, 0, lt);
    print_level(DirectoryName + "/clm_tmp0", clm_tmp, n, 0, lt);
    print_level(DirectoryName + "/tmp10", tmp, n, 10, lt);
    print_level(DirectoryName + "/clm_tmp10", clm_tmp, n, 10, lt);
    print_level(DirectoryName + "/tprb0", tprb, n, 0, lt);

    print_2d_array<int>(DirectoryName + "/flg", flg, n, lt);

    // print lvl2d array
    {
        ofstream o;
        o.open(DirectoryName + "/lvl2d");
        for (int i = 0;  i < n;  i ++)
        for (int j = 0;  j < lt[i];  j ++)
        o
            << j
            << endl;
        o.close();
    }
}    // RTOFSOb::print

}    // namespace rtofs
}    // namespace obsforge
