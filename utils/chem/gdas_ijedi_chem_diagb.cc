#include "chem_diagb.h"
#include "ijedi/Traits.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  gdasapp::ChemDiagB<ijedi::Traits> chemdiagb;
  return run.execute(chemdiagb);
}
