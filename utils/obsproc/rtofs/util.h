#pragma once

#include <stdio.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>


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


// void print_2d_float_array(std::string filename, float ** a, int n, int * dim2);

// template<typename NUMBER>
// void print_2d_array(std::string filename, NUMBER ** a, int n, int * dim2);

void print_level(std::string filename, float ** a, int n, int level, int * dim2);
float * alloc_read_float_array(FILE * f, int n);


std::vector<int> find_unique_values(int * instrument_list, int n);




template<typename NUMBER>
void
    print_2d_array(std::string filename, NUMBER ** a, int n, int * dim2)
{
    std::ofstream o(filename);
    o
        << std::fixed
        << std::setprecision(9);
    for (int i = 0;  i < n;  i ++)
    for (int j = 0;  j < dim2[i];  j ++)
        o
            << a[i] [j]
            << std::endl;
}


}    // namespace rtofs

}    // namespace gdasapp
