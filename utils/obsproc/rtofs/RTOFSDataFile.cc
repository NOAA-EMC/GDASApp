#include <ctime>
#include <string>
#include <sstream>


#include <iostream>
using std::cerr;
using std::endl;
using std::cout;
#include <iomanip>		// std::get_time

#include "RTOFSDataFile.h"
#include "RTOFSOb.h"
#include "util.h"


namespace rtofs
{

typedef char char12[12];
typedef char char7[7];


std::time_t 
	SecondsSinceReferenceTime(char12 time)
{
	std::tm referenceTime = {}; 
	referenceTime.tm_year = 70;  // 1970
	referenceTime.tm_mon = 0;    // January (months are 0-based)
	referenceTime.tm_mday = 1;   // 1st day of the month
	referenceTime.tm_hour = 0;
	referenceTime.tm_min = 0;
	referenceTime.tm_sec = 0;
	std::time_t referenceTimestamp = std::mktime(&referenceTime);

	std::tm t = {};
	std::istringstream ss(time);
	ss >> std::get_time(&t, "%Y%m%d%H%M");

	std::time_t timestamp = std::mktime(&t);
	return std::difftime(timestamp, referenceTimestamp);

}	// SecondsSinceReferenceTime



RTOFSDataFile::
RTOFSDataFile(std::string filename):
	filename(filename)
{

	if (! file_exists(filename))
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

}	// RTOFSDataFile::RTOFSDataFile


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

	char12 * ob_dtg = new char12[n_read];
	fread(ob_dtg, sizeof(char[12]), n_read, f);
	for (int i = 0;  i < n_read;  i ++)
		ob->dtg[i] = SecondsSinceReferenceTime(ob_dtg[i]);

/*
	{
		for (int i = 0;  i < n_read;  i ++)
		{
			for (int j = 0;  j < 12;  j ++)
				cout << ob_dtg[i][j];

			cout 
				<< " = " 
				<< SecondsSinceReferenceTime(ob_dtg[i]) 
				<< " sec" 
				<< endl
			;
			cout << endl;
		}
	}
*/

	skip8bytes(f);

	char12 * ob_rct = new char12[n_read];
	fread(ob_rct, sizeof(char[12]), n_read, f);
	
/*
	{
		for (int i = 0;  i < n_read;  i ++)
		{
			for (int j = 0;  j < 12;  j ++)
				cout << ob_rct[i][j];

			cout 
				<< " = " 
				<< SecondsSinceReferenceTime(ob_rct[i]) 
				<< " sec" 
				<< endl
			;
			cout << endl;
		}
	}
*/


	skip8bytes(f);

	char7 * ob_sgn = new char7[n_read];
	fread(ob_sgn, sizeof(char[7]), n_read, f);

/*
	for (int i = 0;  i < n_read;  i ++)
	{
		// for (int j = 0;  j < 12;  j ++)
			// cout << ob_dtg[i][j];
			// cout << (unsigned int) ob_dtg[i][j] << " ";
			// cout << ob_rct[i][j];
		for (int j = 0;  j < 7;  j ++)
			cout << ob_sgn[i][j];
		cout << endl;
	}
*/

	if (vrsn == 2)
	{
		float ** glb_sal = new float * [n_read];
		for (int i = 0;  i < n_read;  i ++)
		{
			int k = ob->lt[i];
			glb_sal[i] = alloc_read_float_array(f, k);
		}
	}


}	// read_file


}	// namespace rtofs
