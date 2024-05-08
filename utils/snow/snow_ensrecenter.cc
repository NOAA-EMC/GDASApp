#include "snow_ensrecenter.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::FV3SnowEnsRecenter fv3snowensrecenter;
  return run.execute(fv3snowensrecenter);
}
