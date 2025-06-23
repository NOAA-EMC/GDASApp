#include "gdas_meanioda.h"
#include "oops/runs/Run.h"

// this is an example application that
// will use IODA to read a file and print something
// it is intended to be very bare bones
// you will note the .cc file is very empty
// the .h file is where the action is!

int main(int argc, char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::IodaExample iodaexample;
  return run.execute(iodaexample);
}
