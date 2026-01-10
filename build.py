#!/usr/bin/env python3
"""
Build script for C++ example project.
Reads configuration from config.json and builds the project using CMake.
"""

import json
import os
import subprocess
import sys
import shutil
from pathlib import Path


def load_config(config_path="config.json"):
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"✓ Loaded configuration from {config_path}")
        return config
    except FileNotFoundError:
        print(f"✗ Error: Configuration file '{config_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)


def find_compiler(compiler_name):
    """Check if the specified compiler is available."""
    if shutil.which(compiler_name):
        return compiler_name
    
    # If not found, try common alternatives
    if compiler_name == "g++":
        for alt in ["g++", "g++-11", "g++-10", "g++-9"]:
            if shutil.which(alt):
                print(f"⚠ {compiler_name} not found, using {alt} instead")
                return alt
    elif compiler_name == "clang++":
        for alt in ["clang++", "clang++-14", "clang++-13", "clang++-12"]:
            if shutil.which(alt):
                print(f"⚠ {compiler_name} not found, using {alt} instead")
                return alt
    
    print(f"✗ Error: Compiler '{compiler_name}' not found in PATH")
    sys.exit(1)


def run_command(cmd, cwd=None, description=""):
    """Run a command and handle errors."""
    if description:
        print(f"\n→ {description}")
    
    print(f"  Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Command failed with exit code {e.returncode}")
        if e.stdout:
            print(e.stdout)
        return False
    except FileNotFoundError:
        print(f"✗ Command not found: {cmd[0]}")
        return False


def main():
    """Main build function."""
    print("=" * 60)
    print("C++ Example Project - Build Script")
    print("=" * 60)
    
    # Get script directory and project paths
    script_dir = Path(__file__).parent.absolute()
    cpp_example_dir = script_dir / "cpp_example"
    build_dir = script_dir / "build"
    
    # Check if cpp_example directory exists
    if not cpp_example_dir.exists():
        print(f"✗ Error: cpp_example directory not found at {cpp_example_dir}")
        sys.exit(1)
    
    # Load configuration
    config = load_config(script_dir / "config.json")
    
    # Extract configuration values
    compiler = config.get("compiler", "g++")
    cxx_standard = config.get("cxx_standard", "17")
    build_type = config.get("build_type", "Release")
    definitions = config.get("definitions", {})
    compiler_flags = config.get("compiler_flags", [])
    
    # Find the compiler
    compiler_path = find_compiler(compiler)
    
    # Print configuration
    print(f"\nConfiguration:")
    print(f"  Compiler: {compiler_path}")
    print(f"  C++ Standard: {cxx_standard}")
    print(f"  Build Type: {build_type}")
    print(f"  Definitions: {definitions}")
    print(f"  Compiler Flags: {compiler_flags}")
    
    # Create build directory
    if build_dir.exists():
        print(f"\n→ Removing existing build directory")
        shutil.rmtree(build_dir)
    
    print(f"→ Creating build directory: {build_dir}")
    build_dir.mkdir(parents=True, exist_ok=True)
    
    # Prepare CMake command
    cmake_cmd = [
        "cmake",
        str(cpp_example_dir),
        f"-DCMAKE_CXX_COMPILER={compiler_path}",
        f"-DCMAKE_CXX_STANDARD={cxx_standard}",
        f"-DCMAKE_BUILD_TYPE={build_type}"
    ]
    
    # Add definitions
    for key, value in definitions.items():
        cmake_cmd.append(f"-D{key}={value}")
    
    # Add compiler flags
    if compiler_flags:
        flags_str = " ".join(compiler_flags)
        cmake_cmd.append(f"-DCMAKE_CXX_FLAGS={flags_str}")
    
    # Run CMake configuration
    if not run_command(cmake_cmd, cwd=build_dir, description="Configuring CMake"):
        print("\n✗ CMake configuration failed")
        sys.exit(1)
    
    # Run CMake build
    build_cmd = ["cmake", "--build", ".", "--config", build_type]
    if not run_command(build_cmd, cwd=build_dir, description="Building project"):
        print("\n✗ Build failed")
        sys.exit(1)
    
    # Success message
    print("\n" + "=" * 60)
    print("✓ Build completed successfully!")
    print("=" * 60)
    
    executable_path = build_dir / "cpp_example"
    if sys.platform == "win32":
        executable_path = build_dir / build_type / "cpp_example.exe"
    
    if executable_path.exists():
        print(f"\nExecutable created at: {executable_path}")
        print(f"\nTo run the program:")
        print(f"  {executable_path}")
        print(f"\nOr on Unix-like systems:")
        print(f"  ./build/cpp_example")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
