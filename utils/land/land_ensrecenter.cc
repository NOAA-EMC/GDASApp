#include "land_ensrecenter.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::FV3LandEnsRecenter fv3landensrecenter;
  return run.execute(fv3landensrecenter);
}
