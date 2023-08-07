#include "gdas_dumpioda.h"
#include "oops/runs/Run.h"

// this is an example application that
// will use IODA to read a file and print something
// it is intended to be very bare bones

int main(int argc, char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::IodaExample iodaexample;
  return run.execute(iodaexample);
}
