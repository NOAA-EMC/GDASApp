whatis("Description: GDAS build environment common libraries")

help([[Load GDAS Model common libraries]])

-- {["pkg-config"]      = "1.4.2"},
-- {["openblas"]        = "0.3.24"},
-- {["fftw"]            = "3.3.10"},

local gdas_modules = {
  {["cmake"]           = "3.27.9"},
  {["jasper"]          = "2.0.32"},
  {["gettext"]         = "0.22.5"},
  {["curl"]            = "7.81.0"},
  {["zlib-ng"]         = "2.2.1"},
  {["git"]             = "2.34.1"},
  {["hdf5"]            = "1.14.3"},
  {["parallel-netcdf"] = "1.12.3"},
  {["netcdf-c"]        = "4.9.2"},
  {["nccmp"]           = "1.9.0.1"},
  {["netcdf-fortran"]  = "4.6.1"},
  {["nco"]             = "5.2.4"},
  {["parallelio"]      = "2.6.2"},
  {["wget"]            = "1.21.2"},
  {["boost"]           = "1.84.0"},
  {["bufr"]            = "12.1.0"},
  {["git-lfs"]         = "3.0.2"},
  {["ecbuild"]         = "3.7.2"},
  {["openjpeg"]        = "2.3.1"},
  {["eccodes"]         = "2.33.0"},
  {["eigen"]           = "3.4.0"},
  {["eckit"]           = "1.28.3"},
  {["fckit"]           = "0.13.2"},
  {["fiat"]            = "1.4.1"},
  {["ectrans"]         = "1.5.0"},
  {["fms"]             = "2024.02"},
  {["atlas"]           = "0.40.0"},
  {["sp"]              = "2.5.0"},
  {["gsl-lite"]        = "0.37.0"},
  {["libjpeg"]         = "2.1.0"},
  {["krb5"]            = "1.19.2"},
  {["libtirpc"]        = "1.3.3"},
  {["hdf"]             = "4.2.15"},
  {["jedi-cmake"]      = "1.4.0"},
  {["libpng"]          = "1.6.37"},
  {["libxt"]           = "1.3.0"},
  {["libxmu"]          = "1.2.1"},
  {["libxpm"]          = "4.11.0"},
  {["libxaw"]          = "1.0.16"},
  {["udunits"]         = "2.2.28"},
  {["ncview"]          = "2.1.9"},
  {["netcdf-cxx4"]     = "4.3.1"},
  {["json"]            = "3.11.3"},
  {["crtm"]            = "2.4.0.1"},
  {["esmf"]            = "8.8.0"},
  {["prod_util"]       = "2.1.1"},
  {["py-jinja2"]       = "3.1.4"},
  {["py-netcdf4"]      = "1.7.1.post2"},
  {["py-pybind11"]     = "2.13.5"},
  {["py-pycodestyle"]  = "2.11.0"},
  {["py-pyyaml"]       = "6.0"},
  {["py-scipy"]        = "1.14.1"},
  {["py-xarray"]       = "2024.7.0"},
  {["py-f90nml"]       = "1.4.3"},
  {["py-pip"]          = "23.1.2"},
}

for i = 1, #gdas_modules do
  for name, default_version in pairs(gdas_modules[i]) do
    local env_version_name = string.gsub(name, "-", "_") .. "_ver"
    load(pathJoin(name, os.getenv(env_version_name) or default_version))
  end
end
