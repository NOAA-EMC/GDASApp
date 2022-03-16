cmake_minimum_required(VERSION 3.10)

# set the project name
project(GDAS)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

enable_testing()

add_subdirectory(test)
