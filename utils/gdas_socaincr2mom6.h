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
#include "soca/LinearVariableChange/LinearVariableChange.h"
#include "soca/State/State.h"

# include "gdas_postprocincr.h"

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

      // At the very minimum, we run this script to append the layers state, so do that!
      PostProcIncr postProcIncr(fullConfig, geom);
      soca::Increment incr = postProcIncr.appendLayer();

      // Zero out specified fields
      incr = postProcIncr.setToZero(incr);

      // Apply linear change of variables
      incr = postProcIncr.applyLinVarChange(incr);

      // Save final increment
      postProcIncr.save(incr);
      /*
      // get date
      std::string strdt;
      fullConfig.get("date", strdt);
      util::DateTime dt = util::DateTime(strdt);

      // Read the vertical geometry from the background (layer thicknesses)
      soca::Increment layerThick = readLayerThickness(fullConfig, geom);

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
      oops::Variables layerVar = getLayerVarName(fullConfig);
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

      // set specified increment variables to 0.0
      oops::Variables socaZeroIncrVar(fullConfig, "set increment variables to zero");
      std::cout << socaZeroIncrVar << std::endl;

      for (auto & field : socaIncrFs) {
        // only works if rank is 2
        ASSERT(field.rank() == 2);

        // Set data to zero
        if (socaZeroIncrVar.has(field.name())) {
          std::cout << "filed.name(): " << field.name() << std::endl;
          auto view = atlas::array::make_view<double, 2>(field);
          view.assign(0.0);
        }
      }
      socaIncr.fromFieldSet(socaIncrFs);

      // Apply change of variable if in the configuration
      if ( fullConfig.has("linear variable change") ) {
        const eckit::LocalConfiguration trajConfig(fullConfig, "linear variable change.trajectory");
        soca::State xTraj(geom, trajConfig);
        soca::LinearVariableChangeParameters params;
        const eckit::LocalConfiguration lvcConfig(fullConfig, "linear variable change");
        params.deserialize(lvcConfig);
        oops::Log::info() <<  params << std::endl;
        soca::LinearVariableChange lvc(geom, params);
        lvc.changeVarTraj(xTraj, socaIncrVar);
        lvc.changeVarTL(socaIncr, socaIncrVar);
        oops::Log::info() << "incr after var change: " << std::endl << socaIncr << std::endl;
      }

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
      */
      return 0; //result;
    }
    // -----------------------------------------------------------------------------
   private:
    util::DateTime dt_;

    // -----------------------------------------------------------------------------
    std::string appname() const {
      return "gdasapp::SocaIncr2Mom6";
    }
    // -----------------------------------------------------------------------------
    // Read layer thickness from the relevant background
    soca::Increment readLayerThickness(const eckit::Configuration& fullConfig,
                                       const soca::Geometry& geom) const {

      soca::Increment layerThick(geom, getLayerVarName(fullConfig), getDate(fullConfig));
      const eckit::LocalConfiguration vertGeomConfig(fullConfig, "vertical geometry");
      layerThick.read(vertGeomConfig);
      oops::Log::info() << "layerThick: " << std::endl << layerThick << std::endl;

      return layerThick;
    }
    // -----------------------------------------------------------------------------
    util::DateTime getDate(const eckit::Configuration& fullConfig) const {
      std::string strdt;
      fullConfig.get("date", strdt);
      return util::DateTime(strdt);
    }
    // -----------------------------------------------------------------------------
    oops::Variables getLayerVarName(const eckit::Configuration& fullConfig) const {
      oops::Variables layerVar(fullConfig, "layers variable");
      ASSERT(layerVar.size() == 1);
      return layerVar;
    }
  };

}  // namespace gdasapp
