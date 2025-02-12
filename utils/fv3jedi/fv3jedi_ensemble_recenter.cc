#include "fv3jedi_ensemble_recenter.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::EnsembleRecenter EnsembleRecenter;
  return run.execute(EnsembleRecenter);
}
