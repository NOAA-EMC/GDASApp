cmake_minimum_required(VERSION 3.12)

# Find the installed gdas_incr_qc package
find_package(gdas_incr_qc REQUIRED)

# Example executable
add_executable(example_usage example_usage.cc)

target_link_libraries(example_usage PRIVATE
    gdas_incr_qc::gdas_incr_qc
)

target_compile_features(example_usage PRIVATE cxx_std_11)

# Installation
install(TARGETS example_usage
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(FILES example_usage.cc
    DESTINATION ${CMAKE_INSTALL_DOCDIR}/examples
)
