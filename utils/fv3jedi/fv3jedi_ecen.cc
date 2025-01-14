#include "fv3jedi_ecen.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::ecen ecen;
  return run.execute(ecen);
}
