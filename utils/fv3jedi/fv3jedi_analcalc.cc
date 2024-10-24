#include "fv3jedi_analcalc.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::analcalc analcalc;
  return run.execute(analcalc);
}
