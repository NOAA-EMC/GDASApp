project(gdas-utils LANGUAGES C CXX )

find_package(NetCDF REQUIRED COMPONENTS CXX)
find_package(oops REQUIRED)
find_package(atlas REQUIRED)
find_package(soca REQUIRED)

add_subdirectory(soca)
add_subdirectory(ioda_example)
add_subdirectory(test)
