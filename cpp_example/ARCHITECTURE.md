# Network Discovery Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Local Area Network                          │
│                                                                     │
│  ┌─────────────────┐              ┌─────────────────┐             │
│  │   Server Node   │              │   Client Node   │             │
│  │                 │              │                 │             │
│  │ ┌─────────────┐ │              │ ┌─────────────┐ │             │
│  │ │UDP Broadcast│─┼─ Port 8866 ─▶│ │UDP Listener │ │             │
│  │ │  Sender     │ │  Broadcast   │ │             │ │             │
│  │ └─────────────┘ │              │ └─────────────┘ │             │
│  │                 │              │        │        │             │
│  │                 │              │        ▼        │             │
│  │                 │              │ ┌─────────────┐ │             │
│  │ ┌─────────────┐ │              │ │   Device    │ │             │
│  │ │ TCP Server  │ │◀─ Port 9000 ─┤ │  Registry   │ │             │
│  │ │             │ │   Connect    │ └─────────────┘ │             │
│  │ └─────────────┘ │              │        │        │             │
│  │        │        │              │        ▼        │             │
│  │        ▼        │              │ ┌─────────────┐ │             │
│  │ ┌─────────────┐ │              │ │ TCP Client  │ │             │
│  │ │   Handler   │ │◀────────────▶│ │             │ │             │
│  │ │             │ │ JSON Messages│ └─────────────┘ │             │
│  │ └─────────────┘ │              │                 │             │
│  └─────────────────┘              └─────────────────┘             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Discovery Flow

```
Server                                      Client
  │                                           │
  │ 1. Start UDP Broadcaster                 │
  │    (Port 8866)                           │
  ├────────────────────────────────────────▶ │
  │   Broadcast: {                           │ 2. Start UDP Listener
  │     "type": "discovery",                 │    (Port 8866)
  │     "device_id": "...",                  │
  │     "device_name": "MyServer",           │
  │     "tcp_port": 9000                     │
  │   }                                      │
  │                                          │
  │ (Every 5 seconds)                        │
  ├────────────────────────────────────────▶ │
  │                                          │ 3. Receive & Parse
  │                                          │    Extract: IP, Port
  │                                          │    Store in Registry
  │                                          │
  │ 4. Start TCP Server                      │
  │    (Port 9000)                           │
  │                                          │
  │                                          │ 5. User selects device
  │                                          │
  │ ◀────────────────────────────────────────┤ 6. TCP Connect
  │   Connection Established                 │
  │                                          │
  │ 7. Send Welcome                          │
  ├────────────────────────────────────────▶ │
  │   {"type":"response",                    │
  │    "status":"connected",                 │
  │    "message":"Welcome..."}               │
  │                                          │
```

## Communication Flow

```
Client                                      Server
  │                                           │
  │ 1. Send Data                              │
  ├────────────────────────────────────────▶ │
  │   {                                      │ 2. Receive & Process
  │     "type": "data",                      │
  │     "content": "Hello, Server!"          │
  │   }                                      │
  │                                          │
  │                                          │ 3. Send Response
  │ ◀────────────────────────────────────────┤
  │   {                                      │
  │     "type": "response",                  │
  │     "status": "ok",                      │
  │     "message": "Received: Hello..."      │
  │   }                                      │
  │ 4. Display Response                      │
  │                                          │
  │ 5. Send Another Message                  │
  ├────────────────────────────────────────▶ │
  │   ...                                    │
  │                                          │
```

## Class Structure

```
┌──────────────────────────────────────────────────────────────┐
│                     network_discovery.hpp                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────┐                                          │
│  │  JsonHelper    │  Static utility class                    │
│  ├────────────────┤                                          │
│  │ + createDiscoveryMessage()                                │
│  │ + createDataMessage()                                     │
│  │ + createResponseMessage()                                 │
│  │ + parseField()                                            │
│  └────────────────┘                                          │
│                                                               │
│  ┌────────────────┐                                          │
│  │  DeviceInfo    │  Structure                               │
│  ├────────────────┤                                          │
│  │ + device_id                                               │
│  │ + device_name                                             │
│  │ + ip_address                                              │
│  │ + tcp_port                                                │
│  │ + last_seen                                               │
│  └────────────────┘                                          │
│                                                               │
│  ┌────────────────┐                                          │
│  │ UdpBroadcaster │  Sends discovery messages                │
│  ├────────────────┤                                          │
│  │ + start()                                                 │
│  │ + stop()                                                  │
│  │ - broadcastLoop()  // Thread function                    │
│  └────────────────┘                                          │
│                                                               │
│  ┌────────────────┐                                          │
│  │  UdpListener   │  Receives discovery messages             │
│  ├────────────────┤                                          │
│  │ + start(callback)                                         │
│  │ + stop()                                                  │
│  │ - listenLoop()     // Thread function                    │
│  └────────────────┘                                          │
│                                                               │
│  ┌────────────────┐                                          │
│  │   TcpServer    │  Accepts connections                     │
│  ├────────────────┤                                          │
│  │ + start(callback)                                         │
│  │ + stop()                                                  │
│  │ + sendJson()       // Static                             │
│  │ + receiveJson()    // Static                             │
│  │ - acceptLoop()     // Thread function                    │
│  └────────────────┘                                          │
│                                                               │
│  ┌────────────────┐                                          │
│  │   TcpClient    │  Connects to servers                     │
│  ├────────────────┤                                          │
│  │ + connect()                                               │
│  │ + disconnect()                                            │
│  │ + sendJson()                                              │
│  │ + receiveJson()                                           │
│  │ + isConnected()                                           │
│  └────────────────┘                                          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Message Formats

### Discovery Message (UDP Broadcast)
```json
{
  "type": "discovery",
  "device_id": "device_1736518048123456",
  "device_name": "MyServer",
  "tcp_port": 9000
}
```

### Data Message (TCP Client → Server)
```json
{
  "type": "data",
  "content": "Hello, Server! This is my message."
}
```

### Response Message (TCP Server → Client)
```json
{
  "type": "response",
  "status": "ok",
  "message": "Received: Hello, Server! This is my message."
}
```

### Connection Message (TCP Server → Client)
```json
{
  "type": "response",
  "status": "connected",
  "message": "Welcome to MyServer"
}
```

## Threading Model

```
Main Thread
    │
    ├─▶ UdpBroadcaster
    │       └─▶ Broadcast Thread (sends every 5s)
    │
    ├─▶ UdpListener
    │       └─▶ Listen Thread (receives broadcasts)
    │
    ├─▶ TcpServer
    │       ├─▶ Accept Thread (accepts connections)
    │       └─▶ Handler Thread (per client, detached)
    │
    └─▶ TcpClient
            └─▶ Main thread (blocking I/O)
```

## Port Usage

- **UDP Port 8866**: Discovery broadcasts (hardcoded)
- **TCP Port 9000**: Default communication port (configurable)
  - Can be changed when starting server
  - Communicated via discovery message

## Security Notes

⚠️ **This is a demo implementation**. For production:

1. **Authentication**: Add device authentication mechanism
2. **Encryption**: Use TLS/SSL for TCP connections
3. **Input Validation**: Validate all JSON inputs
4. **Rate Limiting**: Prevent broadcast flooding
5. **Access Control**: Implement firewall rules
6. **Secure JSON**: Use a robust JSON library (e.g., nlohmann/json)

## Platform Support

- ✅ **Linux**: Full support with POSIX sockets
- ✅ **macOS**: Full support with POSIX sockets
- ✅ **Windows**: Full support with Winsock2

### Platform-Specific Code

```cpp
#ifdef _WIN32
    // Windows: Winsock2
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
#else
    // Unix/Linux/macOS: POSIX sockets
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <unistd.h>
#endif
```

## Performance Characteristics

- **Broadcast Interval**: 5 seconds
- **Discovery Time**: ~5-10 seconds (wait for broadcast)
- **Connection Setup**: Milliseconds (TCP handshake)
- **Message Latency**: Low (local network)
- **Concurrent Connections**: Unlimited (thread per connection)

## Limitations

1. **No encryption**: All data transmitted in plain text
2. **No authentication**: Any device can connect
3. **Simple JSON parser**: Basic string parsing, not production-ready
4. **Broadcast only**: Won't work across subnets without multicast
5. **No reconnection logic**: Manual reconnection required
6. **No message queuing**: Blocking I/O for simplicity

## Future Enhancements

- [ ] Add TLS/SSL support
- [ ] Implement authentication mechanism
- [ ] Use robust JSON library (nlohmann/json)
- [ ] Add automatic reconnection
- [ ] Support multicast for cross-subnet discovery
- [ ] Add message queuing and async I/O
- [ ] Implement device timeout and cleanup
- [ ] Add heartbeat mechanism
- [ ] Support multiple simultaneous connections per client
