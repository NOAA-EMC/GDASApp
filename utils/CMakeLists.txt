project(gdas-utils LANGUAGES C CXX )

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_FORTRAN_STANDARD 08)
set(CMAKE_FORTRAN_STANDARD_REQUIRED ON)
set(CMAKE_FORTRAN_EXTENSIONS OFF)

find_package(NetCDF REQUIRED COMPONENTS CXX)
find_package(oops REQUIRED)
find_package(atlas REQUIRED)
find_package(soca REQUIRED)
find_package(fv3jedi REQUIRED)

add_subdirectory(soca)
add_subdirectory(ioda_example)
add_subdirectory(test)
add_subdirectory(obsproc)
add_subdirectory(fv3jedi)
