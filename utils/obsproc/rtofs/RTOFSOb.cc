#include <stdio.h>

#include <string>
using std::string;

#include <iostream>
using std::endl;
using std::cerr;

#include <fstream>
using std::ofstream;


#include "RTOFSOb.h"
#include "util.h"


namespace rtofs
{


RTOFSOb::
	RTOFSOb(int n, int mx_lvl, int vrsn):
		n(n),
		mx_lvl(mx_lvl),
		vrsn(vrsn)
{
	dtg = new std::time_t[n];
	allocate();
}



void
RTOFSOb::
	allocate()
{
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
	clm_sal = new float * [n];	// skipped?
	tprb = new float * [n];
	cssd = new float * [n];
	clm_tmp = new float * [n];	// skipped?
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
	if (! file_exists(DirectoryName))
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
	print_int_array(DirectoryName + "/tmp_typ", sal_typ, n);

	print_2d_float_array(DirectoryName + "/tmp", tmp, n, lt);
	print_2d_float_array(DirectoryName + "/sal", sal, n, lt);

	// print lvl2d array
	{
		ofstream o;
		o.open(DirectoryName + "/lvl2d");
		for (int i = 0;  i < n;  i ++)
		for (int j = 0;  j < lt[i];  j ++)
		o
			<< j
			<< endl
		;
		o.close();
	}
}


}	// namespace rtofs
