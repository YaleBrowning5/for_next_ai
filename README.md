# for_next_ai

A learning project for AI with C++ examples including network programming and auto-discovery features.

## Projects

### 1. C++ Example Project
A basic C++ project demonstrating CMake configuration and build automation using Python.

**Location**: `cpp_example/`

**Build and Run**:
```bash
python build.py
./build/cpp_example
```

### 2. Network Auto-Discovery Example
A comprehensive network programming example featuring UDP broadcast-based LAN auto-discovery with TCP communication.

**Location**: `cpp_example/network_example.cpp`

**Features**:
- UDP broadcast for automatic device discovery on port 8866
- TCP connection establishment after discovery
- JSON message format for data exchange
- Cross-platform support (Windows, Linux, macOS)
- Server and client modes

**Build and Run**:
```bash
python build.py
./build/network_example
```

See [NETWORK_README.md](cpp_example/NETWORK_README.md) for detailed usage instructions.

## Building

The project uses a Python build script that reads configuration from `config.json`:

```bash
python build.py
```

This will build all executables in the `build/` directory.

## Requirements

- **CMake**: Version 3.10 or higher
- **C++ Compiler**: GCC, Clang, or MSVC with C++17 support
- **Python**: Version 3.6 or higher (for build script)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/YaleBrowning5/for_next_ai.git
   cd for_next_ai
   ```

2. Build the projects:
   ```bash
   python build.py
   ```

3. Run the examples:
   ```bash
   # Run basic example
   ./build/cpp_example
   
   # Run network discovery demo
   ./build/network_example
   ```

## Network Discovery Demo

The network discovery example demonstrates how to:
1. Broadcast device presence using UDP on port 8866
2. Discover devices on the local network
3. Establish TCP connections to discovered devices
4. Exchange JSON-formatted messages

Try it out by running two instances:
- One as a server (broadcasts and listens)
- One as a client (discovers and connects)

For detailed instructions, see [NETWORK_README.md](cpp_example/NETWORK_README.md).

## License

This is an example project for educational purposes.
