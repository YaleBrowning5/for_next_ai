# Quick Start Guide

## UDP Auto-Discovery with TCP Communication

This guide will help you quickly get started with the LAN auto-discovery feature.

## What You'll Need

- Two terminal windows (or two computers on the same network)
- The compiled `network_example` executable

## Step 1: Build the Project

```bash
cd /path/to/for_next_ai
python build.py
```

This creates:
- `build/network_example` - The discovery demo application

## Step 2: Start the Server

In **Terminal 1**, run:

```bash
./build/network_example
```

Choose option `1` for Server mode:
```
Choose an option: 1
Enter device name: MyServer
Enter TCP port (default 9000): [press Enter]
```

You should see:
```
[SERVER MODE]
✓ UDP Broadcaster started on port 8866
✓ TCP Server started on port 9000
[SERVER] Running... Press Enter to stop
```

The server is now broadcasting its presence every 5 seconds!

## Step 3: Start the Client

In **Terminal 2**, run:

```bash
./build/network_example
```

Choose option `2` for Client mode:
```
Choose an option: 2
```

Wait 10 seconds for device discovery. You should see:
```
[DISCOVERED] Device found:
  ID: device_1736518048123456
  Name: MyServer
  IP: 192.168.1.100
  TCP Port: 9000

[CLIENT] Found 1 device(s)

Select a device to connect:
1. MyServer (192.168.1.100:9000)

Enter device number (or 0 to cancel): 1
```

## Step 4: Send Messages

After connecting, you'll see:
```
✓ Connected successfully
[SERVER SAYS] Welcome to MyServer

[CLIENT] Enter messages to send (type 'quit' to exit):
>
```

Type your message and press Enter:
```
> Hello, Server!
[RESPONSE] Status: ok, Message: Received: Hello, Server!

> How are you?
[RESPONSE] Status: ok, Message: Received: How are you?

> quit
[CLIENT] Disconnecting...
```

In Terminal 1 (server), you'll see:
```
[CONNECTION] Client connected from: 192.168.1.101
[RECEIVED] From 192.168.1.101: {"type":"data","content":"Hello, Server!"}
[RECEIVED] From 192.168.1.101: {"type":"data","content":"How are you?"}
[CONNECTION] Client 192.168.1.101 disconnected
```

## How It Works

1. **Discovery Phase** (UDP Broadcast on port 8866)
   - Server broadcasts: `{"type":"discovery","device_id":"...","device_name":"MyServer","tcp_port":9000}`
   - Client listens and collects device information
   - Client extracts IP address from UDP packet

2. **Connection Phase** (TCP)
   - Client connects to server's IP:port
   - Server accepts connection and sends welcome message

3. **Communication Phase** (JSON over TCP)
   - Client sends: `{"type":"data","content":"Hello!"}`
   - Server responds: `{"type":"response","status":"ok","message":"Received: Hello!"}`

## Testing on a Single Computer

You can test everything on one computer:
- The client will discover the server on localhost (127.0.0.1)
- Open two terminal windows and follow the steps above

## Troubleshooting

### "Failed to start UDP broadcaster"
- Port 8866 might be in use
- Try running with sudo/admin privileges
- Check your firewall settings

### "No devices discovered"
- Make sure the server is running first
- Wait the full 10 seconds for discovery
- Check that both devices are on the same network
- Verify firewall allows UDP port 8866

### "Failed to connect"
- Verify the TCP port number is correct
- Check firewall allows TCP connections
- Ensure server is still running

## Network Requirements

**Firewall Rules:**
- Allow UDP port 8866 (for discovery)
- Allow TCP port 9000 (or your chosen port)

**Linux:**
```bash
sudo ufw allow 8866/udp
sudo ufw allow 9000/tcp
```

**Windows:**
```powershell
netsh advfirewall firewall add rule name="UDP Discovery" dir=in action=allow protocol=UDP localport=8866
netsh advfirewall firewall add rule name="TCP Communication" dir=in action=allow protocol=TCP localport=9000
```

## Next Steps

- Read [NETWORK_README.md](cpp_example/NETWORK_README.md) for detailed documentation
- See [ARCHITECTURE.md](cpp_example/ARCHITECTURE.md) for system design
- Run `python demo_network.py` for an overview

## Example Session

**Server Terminal:**
```
$ ./build/network_example
========================================
LAN Auto-Discovery Demo
UDP Broadcast on Port 8866
========================================
Choose an option: 1
Enter device name: DevServer
Enter TCP port (default 9000): 

[SERVER MODE]
Device ID: device_1736518048123456
✓ UDP Broadcaster started on port 8866
✓ TCP Server started on port 9000

[CONNECTION] Client connected from: 192.168.1.101
[RECEIVED] From 192.168.1.101: {"type":"data","content":"Test message"}
```

**Client Terminal:**
```
$ ./build/network_example
========================================
LAN Auto-Discovery Demo
UDP Broadcast on Port 8866
========================================
Choose an option: 2

[DISCOVERED] Device found:
  Name: DevServer
  IP: 192.168.1.100
  TCP Port: 9000

Select a device to connect:
1. DevServer (192.168.1.100:9000)
Enter device number: 1

✓ Connected successfully
[SERVER SAYS] Welcome to DevServer

> Test message
[RESPONSE] Status: ok, Message: Received: Test message
```

Happy discovering! 🎉
