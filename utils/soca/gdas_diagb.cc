#include "gdas_diagb.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::DiagB diagb;
  return run.execute(diagb);
}
