#include <netcdf>
#include <iostream>
#include <filesystem>

#include "eckit/config/LocalConfiguration.h"

#include "atlas/field.h"

#include "oops/base/PostProcessor.h"
#include "oops/mpi/mpi.h"
#include "oops/runs/Application.h"
#include "oops/util/DateTime.h"
#include "oops/util/Duration.h"
#include "oops/util/Logger.h"

#include "soca/Geometry/Geometry.h"
#include "soca/Increment/Increment.h"

namespace gdasapp {

  class SocaIncr2Mom6 : public oops::Application {
   public:
    explicit SocaIncr2Mom6(const eckit::mpi::Comm & comm = oops::mpi::world())
      : Application(comm) {}
    static const std::string classname() {return "gdasapp::SocaIncr2Mom6";}

    int execute(const eckit::Configuration & fullConfig, bool /*validate*/) const {

      /// Setup the soca geometry
      const eckit::LocalConfiguration geomConfig(fullConfig, "geometry");
      oops::Log::info() << "geometry: " << std::endl << geomConfig << std::endl;
      const soca::Geometry geom(geomConfig, this->getComm());

      /// Setup the vertical geometry from the background (layer thicknesses)
      // get date
      std::string strdt;
      fullConfig.get("date", strdt);
      util::DateTime dt = util::DateTime(strdt);

      // get layer thickness variable name
      oops::Variables layerVar(fullConfig, "layers variable");
      ASSERT(layerVar.size() == 1);

      // read layer thicknesses from the relevant background
      soca::Increment layerThick(geom, layerVar, dt);
      const eckit::LocalConfiguration vertGeomConfig(fullConfig, "vertical geometry");
      layerThick.read(vertGeomConfig);
      oops::Log::info() << "layerThick: " << std::endl << layerThick << std::endl;

      // Setup the soca increment
      // get the increment variables
      oops::Variables socaIncrVar(fullConfig, "increment variables");
      ASSERT(socaIncrVar.size() >= 1);

      // read the soca increment
      soca::Increment socaIncr(geom, socaIncrVar, dt);
      const eckit::LocalConfiguration socaIncrConfig(fullConfig, "soca increment");
      socaIncr.read(socaIncrConfig);
      oops::Log::info() << "socaIncr: " << std::endl << socaIncr << std::endl;

      /// Create the MOM6 IAU increment
      // concatenate variables
      oops::Variables mom6IauVar(socaIncrVar);
      mom6IauVar += layerVar;
      oops::Log::info() << "mom6IauVar: " << std::endl << mom6IauVar << std::endl;

      // append layer variable to soca increment
      atlas::FieldSet socaIncrFs;
      socaIncr.toFieldSet(socaIncrFs);
      socaIncr.updateFields(mom6IauVar);
      oops::Log::info() << "MOM6 incr: " << std::endl << socaIncr << std::endl;

      // pad layer increment with zeros
      atlas::FieldSet socaLayerThickFs;
      layerThick.toFieldSet(socaLayerThickFs);
      layerThick.updateFields(mom6IauVar);
      oops::Log::info() << "h: " << std::endl << layerThick << std::endl;

      // append layer thinckness to increment
      socaIncr += layerThick;
      oops::Log::info() << "MOM6 IAU increment: " << std::endl << socaIncr << std::endl;

      // Save MOM6 IAU Increment
      const eckit::LocalConfiguration mom6IauConfig(fullConfig, "mom6 iau increment");
      socaIncr.write(mom6IauConfig);

      // TODO: the "checkpoint" script expects the ocean increment output to
      //       be in "inc.nc". Remove what's below, eventually
      std::string datadir;
      mom6IauConfig.get("datadir", datadir);
      std::filesystem::path pathToResolve = datadir;
      std::string exp;
      mom6IauConfig.get("exp", exp);
      std::string outputType;
      mom6IauConfig.get("type", outputType);
      std::string incrFname = std::filesystem::canonical(pathToResolve);
      incrFname += "/ocn." + exp + "." + outputType + "." + dt.toString() + ".nc";
      const char* charPtr = incrFname.c_str();
      oops::Log::info() << "rename: " << incrFname << " to " << "inc.nc" << std::endl;
      int result = std::rename(charPtr, "inc.nc");

      return result;
    }
    // -----------------------------------------------------------------------------
   private:
    std::string appname() const {
      return "gdasapp::SocaIncr2Mom6";
    }
    // -----------------------------------------------------------------------------
  };

}  // namespace gdasapp
