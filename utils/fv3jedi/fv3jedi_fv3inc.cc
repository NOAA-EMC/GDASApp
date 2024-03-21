#include "fv3jedi_fv3inc.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::fv3inc fv3inc;
  return run.execute(fv3inc);
}
