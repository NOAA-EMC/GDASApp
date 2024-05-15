#ifndef BUNDLE_GDAS_UTILS_OBSPROC_RTOFS_UTIL_H_
#define BUNDLE_GDAS_UTILS_OBSPROC_RTOFS_UTIL_H_

#include <stdio.h>
#include <string>

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
float * alloc_read_float_array(FILE * f, int n);

}    // namespace rtofs


#endif    // BUNDLE_GDAS_UTILS_OBSPROC_RTOFS_UTIL_H_
