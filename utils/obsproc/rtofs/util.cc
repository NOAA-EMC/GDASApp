#include "util.h"

#include <sys/stat.h>                // used in file_exists

#include <fstream>
using std::ofstream;

#include <iomanip>
using std::setprecision;

#include <iostream>
using std::cerr;
using std::endl;
using std::cout;



namespace gdasapp
{

namespace rtofs
{


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


}    // namespace rtofs

}    // namespace gdasapp
