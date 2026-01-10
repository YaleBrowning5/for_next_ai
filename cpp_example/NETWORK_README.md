# Network Discovery Example

This example demonstrates UDP broadcast-based LAN auto-discovery with TCP communication using JSON message format.

## Features

- **UDP Broadcast Discovery**: Automatically discover devices on the local network using UDP broadcast on port 8866
- **TCP Communication**: Establish reliable TCP connections after discovery
- **JSON Message Format**: All messages are transmitted in JSON format for easy parsing and interoperability
- **Cross-platform**: Works on Windows, Linux, and macOS

## Architecture

### Components

1. **UDP Broadcaster**: Broadcasts device information every 5 seconds on port 8866
2. **UDP Listener**: Listens for broadcast messages and discovers devices
3. **TCP Server**: Accepts incoming connections from clients
4. **TCP Client**: Connects to discovered devices
5. **JSON Helper**: Utilities for creating and parsing JSON messages

### Discovery Protocol

1. Server broadcasts its information via UDP:
   ```json
   {
     "type": "discovery",
     "device_id": "device_1234567890",
     "device_name": "My Server",
     "tcp_port": 9000
   }
   ```

2. Client receives broadcast and extracts device information
3. Client establishes TCP connection to the server's IP and port
4. Communication proceeds using JSON messages

### Message Types

**Data Message** (Client to Server):
```json
{
  "type": "data",
  "content": "Hello, Server!"
}
```

**Response Message** (Server to Client):
```json
{
  "type": "response",
  "status": "ok",
  "message": "Received: Hello, Server!"
}
```

## Building

### Using Python Build Script

```bash
cd /path/to/for_next_ai
python build.py
```

The build script will create both executables:
- `build/cpp_example` - Original example
- `build/network_example` - Network discovery demo

### Manual Build

```bash
mkdir -p build
cd build
cmake ../cpp_example
cmake --build .
```

## Usage

### Running as Server

1. Start the network example:
   ```bash
   ./build/network_example
   ```

2. Choose option `1` (Start as Server)

3. Enter a device name (e.g., "MyServer")

4. Enter a TCP port (press Enter for default 9000)

5. The server will start broadcasting its presence and accept connections

**Example:**
```
Choose an option: 1

Enter device name: MyServer
Enter TCP port (default 9000): 

[SERVER MODE]
Device ID: device_1736518048123456
Device Name: MyServer
TCP Port: 9000
Discovery Port: 8866

✓ UDP Broadcaster started on port 8866
✓ TCP Server started on port 9000

[SERVER] Running... Press Enter to stop
```

### Running as Client

1. Start another instance of the network example:
   ```bash
   ./build/network_example
   ```

2. Choose option `2` (Start as Client)

3. Wait for device discovery (10 seconds)

4. Select a discovered device from the list

5. Send messages interactively

**Example:**
```
Choose an option: 2

[CLIENT MODE]
Listening for devices on port 8866...
✓ UDP Listener started

Scanning for 10 seconds...

[DISCOVERED] Device found:
  ID: device_1736518048123456
  Name: MyServer
  IP: 192.168.1.100
  TCP Port: 9000

[CLIENT] Found 1 device(s)

Select a device to connect:
1. MyServer (192.168.1.100:9000)

Enter device number (or 0 to cancel): 1

[CLIENT] Connecting to MyServer at 192.168.1.100:9000
✓ Connected successfully
[SERVER SAYS] Welcome to MyServer

[CLIENT] Enter messages to send (type 'quit' to exit):
> Hello, Server!
[RESPONSE] Status: ok, Message: Received: Hello, Server!
> quit

[CLIENT] Disconnecting...
[CLIENT] Stopped
```

## Network Configuration

### Ports

- **UDP Discovery Port**: 8866 (hardcoded)
- **TCP Communication Port**: Configurable (default 9000)

### Firewall Configuration

Make sure to allow:
- UDP port 8866 for discovery
- TCP port 9000 (or your chosen port) for communication

**Linux (ufw):**
```bash
sudo ufw allow 8866/udp
sudo ufw allow 9000/tcp
```

**Windows Firewall:**
```powershell
netsh advfirewall firewall add rule name="UDP Discovery" dir=in action=allow protocol=UDP localport=8866
netsh advfirewall firewall add rule name="TCP Communication" dir=in action=allow protocol=TCP localport=9000
```

## Code Structure

### network_discovery.hpp

Header-only library containing all network classes:

- `JsonHelper`: JSON utility functions for creating and parsing messages
- `DeviceInfo`: Structure to store discovered device information
- `UdpBroadcaster`: Broadcasts device presence on the network
- `UdpListener`: Listens for device broadcasts
- `TcpServer`: Accepts and handles client connections
- `TcpClient`: Connects to servers and sends/receives messages

### network_example.cpp

Demo application showing:
- Server mode with broadcasting and TCP server
- Client mode with discovery and TCP client
- Interactive message exchange

## API Usage

### Simple Server Example

```cpp
#include "network_discovery.hpp"

// Start UDP broadcaster
UdpBroadcaster broadcaster("my_device_id", "My Device", 9000);
broadcaster.start();

// Start TCP server
TcpServer server(9000);
server.start([](SOCKET client_sock, const std::string& client_ip) {
    std::string message = TcpServer::receiveJson(client_sock);
    std::string response = JsonHelper::createResponseMessage("ok", "Received");
    TcpServer::sendJson(client_sock, response);
});

// Keep running...
```

### Simple Client Example

```cpp
#include "network_discovery.hpp"

// Discover devices
UdpListener listener;
listener.start([](const DeviceInfo& device) {
    std::cout << "Found: " << device.device_name << std::endl;
});

// Wait for discovery...

// Connect to device
TcpClient client;
client.connect("192.168.1.100", 9000);

// Send message
std::string message = JsonHelper::createDataMessage("Hello!");
client.sendJson(message);

// Receive response
std::string response = client.receiveJson();
```

## Testing on Local Machine

To test on a single machine:

1. Open two terminal windows
2. In terminal 1: Run as server
3. In terminal 2: Run as client
4. The client will discover the server on localhost (127.0.0.1)
5. Send messages between them

## Troubleshooting

### "Failed to start UDP broadcaster"

- Check if port 8866 is already in use
- Verify network interface is available
- Run with administrator/root privileges if needed

### "No devices discovered"

- Ensure server is running and broadcasting
- Check firewall rules allow UDP port 8866
- Verify both devices are on the same network
- Some networks may block broadcast packets

### "Failed to connect"

- Verify TCP port is correct
- Check firewall allows TCP connections
- Ensure server is listening on the correct port
- Verify IP address is reachable

## Security Considerations

This is a demo application. For production use:

- Add authentication mechanism
- Implement encryption (TLS/SSL)
- Validate and sanitize all inputs
- Add rate limiting
- Implement proper error handling
- Use secure JSON parsing library

## License

This is an example project for educational purposes.
