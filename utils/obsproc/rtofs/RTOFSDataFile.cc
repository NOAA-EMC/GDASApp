#include <iostream>
using std::cerr;
using std::endl;

#include <fstream>
using std::ofstream;

#include "RTOFSDataFile.h"
#include "util.h"


namespace gdasapp
{
namespace rtofs
{


RTOFSDataFile::
RTOFSDataFile(std::string filename)
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

    ob->read(f);

    skip8bytes(f);

    fread(ob->dtg, sizeof(RTOFSOb::char12), n_read, f);

    skip8bytes(f);

    RTOFSOb::char12 * ob_rct = new RTOFSOb::char12[n_read];
    fread(ob_rct, sizeof(RTOFSOb::char12), n_read, f);

    skip8bytes(f);

    RTOFSOb::char7 * ob_sgn = new RTOFSOb::char7[n_read];
    fread(ob_sgn, sizeof(RTOFSOb::char7), n_read, f);

#ifdef RTOFS_OUTPUT_SGN
    // we don't know what sgn is.
    // by default, it is not output
    {
        ofstream o("sgn");
        for (int i = 0;  i < n_read;  i ++)
        {
            for (int k = 0;  k < 7; k ++)
                o << ob_sgn[i][k];
            o << std::endl;
        }
    }
#endif    // RTOFS_OUTPUT_SGN

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
}    // RTOFSDataFile::read_file

}    // namespace rtofs
}    // namespace gdasapp
