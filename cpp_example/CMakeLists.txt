cmake_minimum_required(VERSION 3.10)

# Project name
project(CppExample VERSION 1.0)

# Set C++ standard (can be overridden via command line)
if(NOT DEFINED CMAKE_CXX_STANDARD)
    set(CMAKE_CXX_STANDARD 17)
endif()
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Print compiler information
message(STATUS "C++ Compiler: ${CMAKE_CXX_COMPILER}")
message(STATUS "C++ Standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")

# Create executable
add_executable(cpp_example main.cpp)

# Add macro definitions if provided
if(DEFINED VERSION)
    target_compile_definitions(cpp_example PRIVATE VERSION=${VERSION})
    message(STATUS "VERSION defined as: ${VERSION}")
endif()

if(DEFINED DEBUG_MODE)
    target_compile_definitions(cpp_example PRIVATE DEBUG_MODE=${DEBUG_MODE})
    message(STATUS "DEBUG_MODE defined as: ${DEBUG_MODE}")
endif()

if(DEFINED ENABLE_LOGGING)
    target_compile_definitions(cpp_example PRIVATE ENABLE_LOGGING=${ENABLE_LOGGING})
    message(STATUS "ENABLE_LOGGING defined as: ${ENABLE_LOGGING}")
endif()

# Add any additional compile definitions
# These can be passed via -D flags to CMake
