#ifndef RTOFSDataFile__H
#define RTOFSDataFile__H

#include <string>


namespace rtofs
{

class RTOFSOb;

class RTOFSDataFile
{
public:
	RTOFSDataFile(std::string filename);
	int NumberOfObservations() { return nobs; }
	RTOFSOb & observations() { return * ob; }


private:
	std::string filename;
	int nobs;
	FILE * f;
	RTOFSOb * ob;

	void read_file();

};	// class RTOFSDataFile

}	// namespace rtofs


#endif	// RTOFSDataFile__H
