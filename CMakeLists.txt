cmake_minimum_required(VERSION 3.10)

# set the project name
project(GDASApp)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

enable_testing()

add_subdirectory(src)
add_subdirectory(ush)
add_subdirectory(test)
