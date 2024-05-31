#pragma once

#include <stdio.h>
// #define _BSD_SOURCE
#include <endian.h>
#include <sys/stat.h>                // used in file_exists

#include <ctime>
#include <fstream>
using std::ofstream;
#include <iomanip>        // std::get_time
using std::setprecision;
#include <iostream>
using std::cerr;
using std::endl;
using std::cout;
#include <netcdf>    // NOLINT (using C API)
#include <string>
using std::string;
#include <sstream>
#include <vector>
using std::vector;

#include "NetCDFToIodaConverter.h"
#include "oops/util/dateFunctions.h"
#include "oops/util/DateTime.h"






namespace gdasapp
{


namespace rtofs
{

bool file_exists(const std::string& name);

void skip8bytes(FILE * f);
int read_int(FILE * f);
void read_float_array(FILE * f, float * a, int n);
void read_int_array(FILE * f, int * a, int n);

void print_float_array(std::string filename, float * a, int n);
void print_int_array(std::string filename, int * a, int n);
void print_2d_float_array(std::string filename, float ** a, int n, int * dim2);
template<typename NUMBER>
void print_2d_array(std::string filename, NUMBER ** a, int n, int * dim2);
void print_level(std::string filename, float ** a, int n, int level, int * dim2);
float * alloc_read_float_array(FILE * f, int n);

std::vector<int> find_unique_values(int * instrument_list, int n);


class RTOFSOb
{
 public:
    RTOFSOb(int n, int mx_lvl, int vrsn);

    typedef char char12[12];
    typedef char char7[7];

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


int
RTOFSOb::
    TotalNumberOfValues()
{
    int NumberOfValues = 0;
    for (int i = 0;  i < n;  i ++)
        NumberOfValues += lt[i];
    return NumberOfValues;
}



class RTOFSDataFile
{
 public:
    explicit RTOFSDataFile(std::string filename);
    RTOFSOb & observations() { return * ob; }


 private:
    std::string filename;
    int nobs;
    FILE * f;
    RTOFSOb * ob;

    void read_file();
};    // class RTOFSDataFile



int64_t
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

    gdasapp::obsproc::iodavars::IodaVars TemperatureIodaVars();
    gdasapp::obsproc::iodavars::IodaVars SalinityIodaVars();

 private:
    // Read binary file and populate iodaVars
    virtual gdasapp::obsproc::iodavars::IodaVars
        providerToIodaVars(const std::string filename) = 0;

    rtofs::RTOFSOb * pob;
};  // class RTOFSInSitu


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

    std::vector<int> tmp_instrument =
        rtofs::find_unique_values(ob.tmp_typ, n);

    std::vector<int> sal_instrument =
        rtofs::find_unique_values(ob.sal_typ, n);
}    // RTOFSInSitu::ProcessFile



gdasapp::obsproc::iodavars::IodaVars
RTOFSInSitu::
    TemperatureIodaVars()
{
    // Set the int metadata names
    std::vector<std::string> intMetadataNames = {"tmp_typ"};

    // Set the float metadata name
    std::vector<std::string> floatMetadataNames = {"level"};
    rtofs::RTOFSOb & ob = * pob;

    gdasapp::obsproc::iodavars::IodaVars iodaVars(
        ob.TotalNumberOfValues(),
        floatMetadataNames,
        intMetadataNames);

    iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";
    iodaVars.niMetadata_ = 1;
    iodaVars.nfMetadata_ = 1;

    int n = ob.NumberOfObservations();

    int k = 0;
    for (int i = 0;  i < n;  i ++)
    {
        int64_t date = SecondsSinceReferenceTime(ob.dtg[i]);

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
}    // RTOFSInSitu::TemperatureIodaVars






gdasapp::obsproc::iodavars::IodaVars
RTOFSInSitu::
    SalinityIodaVars()
{
    // Set the int metadata names
    std::vector<std::string> intMetadataNames = {"sal_typ"};

    // Set the float metadata name
    std::vector<std::string> floatMetadataNames = {"level"};

    rtofs::RTOFSOb & ob = * pob;

    gdasapp::obsproc::iodavars::IodaVars iodaVars(
        ob.TotalNumberOfValues(),
        floatMetadataNames,
        intMetadataNames);

    iodaVars.referenceDate_ = "seconds since 1970-01-01T00:00:00Z";
    iodaVars.niMetadata_ = 1;
    iodaVars.nfMetadata_ = 1;

    int n = ob.NumberOfObservations();

    int k = 0;
    for (int i = 0;  i < n;  i ++)
    {
        int64_t date = SecondsSinceReferenceTime(ob.dtg[i]);

        for (int j = 0;  j < ob.lt[i];  j ++)
        {
            iodaVars.longitude_(k) = ob.lon[i];
            iodaVars.latitude_(k) = ob.lat[i];
            iodaVars.obsVal_(k) = ob.sal[i][j];
            iodaVars.obsError_(k) = ob.sal_err[i][j];
            iodaVars.datetime_(k) = date;
            iodaVars.preQc_(k) = ob.flg[i][j];
            iodaVars.intMetadata_.row(k) << ob.sal_typ[i];
            iodaVars.floatMetadata_.row(k) << ob.lvl[i][j];

            k++;
        }
    }

    return iodaVars;
}    // RTOFSInSitu::SalinityIodaVars







std::vector<int>
    find_unique_values(int * instrument_list, int n)
{
    std::vector<int> instrument;

    // Function to insert a value while keeping
    // the vector sorted and without duplicates
    auto insertUniqueSorted = [&](int value)
    {
        auto it = std::lower_bound(instrument.begin(), instrument.end(), value);
        if (it == instrument.end() || *it != value)
            instrument.insert(it, value);
    };

    for (int i = 0;  i < n;  i ++)
        insertUniqueSorted(instrument_list[i]);

    return instrument;
}



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
    clm_sal = new float * [n];    // skipped?
    tprb = new float * [n];
    cssd = new float * [n];
    clm_tmp = new float * [n];    // skipped?
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

    print_2d_float_array(DirectoryName + "/tmp", tmp, n, lt);
    print_2d_float_array(DirectoryName + "/sal", sal, n, lt);
    print_2d_float_array(DirectoryName + "/lvl", lvl, n, lt);
    print_2d_float_array(DirectoryName + "/cssd", cssd, n, lt);
    print_2d_float_array(DirectoryName + "/ctsd", ctsd, n, lt);
    print_2d_float_array(DirectoryName + "/tprb", tprb, n, lt);
    print_2d_float_array(DirectoryName + "/sprb", sprb, n, lt);
    print_2d_float_array(DirectoryName + "/clm_tmp", clm_tmp, n, lt);

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



RTOFSDataFile::
RTOFSDataFile(std::string filename):
    filename(filename)
{
    if (!file_exists(filename))
    {
        cerr << "File not found" << endl;
        exit(1);
    }


    const char * fn = filename.c_str();
    f = fopen(fn, "rb");
    if (!f)
    {
        cerr << "Error opening file " << fn << endl;
        exit(1);
    }

    read_file();
}    // RTOFSDataFile::RTOFSDataFile


void
RTOFSDataFile::
    read_file()
{
    fseek(f, 4, SEEK_CUR);

    int n_read = read_int(f);
    int mx_lvl = read_int(f);
    int vrsn = read_int(f);

    ob = new RTOFSOb(n_read, mx_lvl, vrsn);
    nobs = n_read;

    ob->read(f);

    skip8bytes(f);

    fread(ob->dtg, sizeof(RTOFSOb::char12), n_read, f);

    skip8bytes(f);

    RTOFSOb::char12 * ob_rct = new RTOFSOb::char12[n_read];
    fread(ob_rct, sizeof(RTOFSOb::char12), n_read, f);

    skip8bytes(f);

    RTOFSOb::char7 * ob_sgn = new RTOFSOb::char7[n_read];
    fread(ob_sgn, sizeof(RTOFSOb::char7), n_read, f);

    // we don't know what sgn is.
    {
        ofstream o("sgn");
        for (int i = 0;  i < n_read;  i ++)
        {
            for (int k = 0;  k < 7; k ++)
                o << ob_sgn[i][k];
            o << std::endl;
        }
    }

    // we never had an input file with vrsn == 2
    if (vrsn == 2)
    {
        float ** glb_sal = new float * [n_read];
        for (int i = 0;  i < n_read;  i ++)
        {
            int k = ob->lt[i];
            glb_sal[i] = alloc_read_float_array(f, k);
        }
    }
}    // read_file



void skip8bytes(FILE * f)
{
    fseek(f, 8, SEEK_CUR);
}


void
    read_float_array(FILE * f, float * a, int n)
{
    skip8bytes(f);

    fread(a, sizeof(float), n, f);

    uint32_t * data = reinterpret_cast<uint32_t *>(a);

    for (int i = 0;  i < n;  i ++)
        data[i] = be32toh(data[i]);
}    // read_float_array


void
    read_int_array(FILE * f, int * a, int n)
{
    skip8bytes(f);

    fread(a, sizeof(int), n, f);

    uint32_t * data = reinterpret_cast<uint32_t *>(a);

    for (int i = 0;  i < n;  i ++)
        data[i] = be32toh(data[i]);
}    // read_int_array



void
    print_level(std::string filename, float ** a, int n, int level, int * dim2)
{
    ofstream o(filename);
    o
        << std::fixed
        << std::setprecision(9);

    for (int i = 0;  i < n;  i ++)
    if (level < dim2[i])
        o
            << a[i] [level]
            << endl;

    o.close();
}


void
    print_int_array(std::string filename, int * a, int n)
{
    ofstream o(filename);
    for (int i = 0;  i < n;  i ++)
        o
            << a[i]
            << endl;
    o.close();
}


void
    print_float_array(std::string filename, float * a, int n)
{
    ofstream o(filename);
    o
        << std::fixed
        << std::setprecision(9);
    for (int i = 0;  i < n;  i ++)
        o
            << a[i]
            << endl;
}

void
    print_2d_float_array(std::string filename, float ** a, int n, int * dim2)
{
    ofstream o(filename);
    o
        << std::fixed
        << std::setprecision(9);
    for (int i = 0;  i < n;  i ++)
    for (int j = 0;  j < dim2[i];  j ++)
        o
            << a[i] [j]
            << endl;
}


template<typename NUMBER>
void
    print_2d_array(std::string filename, NUMBER ** a, int n, int * dim2)
{
    ofstream o(filename);
    o
        << std::fixed
        << std::setprecision(9);
    for (int i = 0;  i < n;  i ++)
    for (int j = 0;  j < dim2[i];  j ++)
        o
            << a[i] [j]
            << endl;
}


bool
    file_exists(const std::string& name)
{
    struct stat buffer;
    return (stat (name.c_str(), &buffer) == 0);
}


int
    read_int(FILE * f)
{
    int dummy;
    fread(&dummy, sizeof(int), 1, f);
    dummy = static_cast<int>(be32toh(dummy));
    return dummy;
}    // read_int



void
    read_real_array(FILE * f, float * a, int n)
{
    fread(a, sizeof(float), n, f);

    uint32_t * data = reinterpret_cast<uint32_t *>(a);

    for (int i = 0;  i < n;  i ++)
        data[i] = be32toh(data[i]);
}    // read_real_array


float *
    alloc_read_float_array(FILE * f, int n)
{
    float * a = new float[n];
    skip8bytes(f);
    read_real_array(f, a, n);
    return a;
}


void
    print_int_array(int * a, int n)
{
    for (int i = 0;  i < n;  i ++)
        cout
            << a[i]
            << endl;
}


int *
    alloc_read_int_array(FILE * f, int n)
{
    int * a = new int[n];
    skip8bytes(f);
    read_int_array(f, a, n);
    return a;
}


void
    print_real_array(float * a, int n)
{
    cout
        << std::fixed
        << std::setprecision(9);
    for (int i = 0;  i < n;  i ++)
        cout
            << a[i]
            << endl;
}


}    // namespace rtofs

}  // namespace gdasapp
