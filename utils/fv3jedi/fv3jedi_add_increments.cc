#include "fv3jedi_add_increments.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::AddIncrements AddIncrements;
  return run.execute(AddIncrements);
}
