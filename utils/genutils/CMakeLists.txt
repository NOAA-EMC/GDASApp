# Create a library from all source files in this directory
set(oops_utils_srcs
    Flood.h
    Flood.cc
)

add_library(gdasapp_utils_oops ${oops_utils_srcs})

target_compile_features(gdasapp_utils_oops PUBLIC cxx_std_17)

# Optionally, specify include directories if needed
# target_include_directories(gdasapp_utils_oops PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# Optionally, link dependencies if required
target_link_libraries(gdasapp_utils_oops PUBLIC oops atlas)
