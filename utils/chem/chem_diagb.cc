#include "chem_diagb.h"
#include "oops/runs/Run.h"

int main(int argc,  char ** argv) {
  oops::Run run(argc, argv);
  std::cout << "argv = " << argv ; 
  gdasapp::FV3ChemDiagB fv3chemdiagb;
  return run.execute(fv3chemdiagb);
}
