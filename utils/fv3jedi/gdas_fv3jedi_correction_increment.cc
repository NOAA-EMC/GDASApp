#include "fv3jedi_correction_increment.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::CorrectionIncrement CorrectionIncrement;
  return run.execute(CorrectionIncrement);
}
