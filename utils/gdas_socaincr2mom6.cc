#include "gdas_socaincr2mom6.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::SocaIncr2Mom6 socaincr2mom6;
  return run.execute(socaincr2mom6);
}
