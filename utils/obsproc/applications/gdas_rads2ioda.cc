#include "gdas_rads2ioda.h"
#include "oops/runs/Run.h"

int main(int argc, char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::Rads2IodaApp rads2iodaapp;
  return run.execute(rads2iodaapp);
}
