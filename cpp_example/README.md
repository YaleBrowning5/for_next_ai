# C++ Example Project

This is a simple C++ example project that demonstrates how to use CMake with a Python build script and JSON configuration file.

## Overview

The project consists of:
- **main.cpp**: A simple C++ program that displays macro definitions and compiler information
- **CMakeLists.txt**: CMake configuration file
- **config.json**: JSON configuration file for build settings
- **build.py**: Python script that reads config.json and builds the project

## Features

- Demonstrates using macro definitions (VERSION, DEBUG_MODE, ENABLE_LOGGING)
- Prints compiler information at runtime
- Uses CMake for cross-platform building
- Configuration-driven build process via JSON
- Python build script for easy automation

## Quick Start

### Using the Python Build Script (Recommended)

Simply run the build script from the repository root:

```bash
python build.py
```

Or make it executable and run directly:

```bash
chmod +x build.py
./build.py
```

The script will:
1. Read configuration from `config.json`
2. Configure CMake with the specified settings
3. Build the project
4. Report the location of the executable

### Running the Executable

After building, run the executable:

```bash
./build/cpp_example
```

You should see output showing the configuration, compiler information, and a demo message.

## Configuration

Edit `config.json` in the repository root to customize the build:

```json
{
  "compiler": "g++",           // C++ compiler to use
  "cxx_standard": "17",        // C++ standard version
  "build_type": "Release",     // Build type: Debug, Release, etc.
  "definitions": {             // Macro definitions passed to the compiler
    "VERSION": "1.0.0",
    "DEBUG_MODE": "ON",
    "ENABLE_LOGGING": "true"
  },
  "compiler_flags": [          // Additional compiler flags
    "-Wall",
    "-Wextra"
  ]
}
```

### Configuration Options

- **compiler**: The C++ compiler to use (e.g., `g++`, `clang++`, `cl`)
- **cxx_standard**: C++ standard version (e.g., `11`, `14`, `17`, `20`)
- **build_type**: CMake build type (`Debug`, `Release`, `RelWithDebInfo`, `MinSizeRel`)
- **definitions**: Key-value pairs for macro definitions
- **compiler_flags**: Additional compiler flags (e.g., `-Wall`, `-O3`)

## Manual Build (Without Python Script)

If you prefer to build manually without the Python script:

```bash
# Create build directory
mkdir -p build
cd build

# Configure CMake
cmake ../cpp_example \
  -DCMAKE_CXX_COMPILER=g++ \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_BUILD_TYPE=Release \
  -DVERSION=1.0.0 \
  -DDEBUG_MODE=ON \
  -DENABLE_LOGGING=true \
  -DCMAKE_CXX_FLAGS="-Wall -Wextra"

# Build
cmake --build . --config Release

# Run
./cpp_example
```

## Requirements

- **CMake**: Version 3.10 or higher
- **C++ Compiler**: GCC, Clang, or MSVC with C++17 support
- **Python**: Version 3.6 or higher (for build.py)

## Project Structure

```
for_next_ai/
├── config.json              # Build configuration
├── build.py                 # Python build script
├── cpp_example/
│   ├── main.cpp            # C++ source code
│   ├── CMakeLists.txt      # CMake configuration
│   └── README.md           # This file
└── build/                  # Build directory (created by build.py)
    └── cpp_example         # Compiled executable
```

## Customization

### Adding New Macro Definitions

1. Add the definition to `config.json`:
   ```json
   "definitions": {
     "MY_MACRO": "my_value"
   }
   ```

2. Use it in `main.cpp`:
   ```cpp
   #ifndef MY_MACRO
   #define MY_MACRO "default_value"
   #endif
   ```

3. Rebuild with `python build.py`

### Changing Compiler

Edit `config.json` and change the `compiler` field:

```json
{
  "compiler": "clang++"
}
```

### Adding Source Files

1. Add your `.cpp` file to the `cpp_example/` directory
2. Update `CMakeLists.txt`:
   ```cmake
   add_executable(cpp_example main.cpp your_file.cpp)
   ```

## Troubleshooting

### Compiler Not Found

If you get a "compiler not found" error, make sure:
- The compiler is installed on your system
- The compiler is in your system's PATH
- The compiler name in `config.json` matches your installation

### CMake Not Found

Install CMake:
- **Ubuntu/Debian**: `sudo apt-get install cmake`
- **macOS**: `brew install cmake`
- **Windows**: Download from [cmake.org](https://cmake.org/download/)

### Build Errors

1. Clean the build directory: `rm -rf build`
2. Try building again: `python build.py`
3. Check the error messages for specific issues

## License

This is an example project for educational purposes.
