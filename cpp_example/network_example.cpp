#include <iostream>
#include <string>
#include <map>
#include <chrono>
#include <thread>
#include "network_discovery.hpp"

using namespace network;

// Device registry to track discovered devices
class DeviceRegistry {
public:
    void addDevice(const DeviceInfo& device) {
        std::lock_guard<std::mutex> lock(mutex_);
        devices_[device.device_id] = device;
    }
    
    std::vector<DeviceInfo> getDevices() {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<DeviceInfo> result;
        for (const auto& pair : devices_) {
            result.push_back(pair.second);
        }
        return result;
    }
    
    bool hasDevices() {
        std::lock_guard<std::mutex> lock(mutex_);
        return !devices_.empty();
    }

private:
    std::map<std::string, DeviceInfo> devices_;
    std::mutex mutex_;
};

void printMenu() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "Network Discovery Demo" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "1. Start as Server (broadcast & listen)" << std::endl;
    std::cout << "2. Start as Client (discover & connect)" << std::endl;
    std::cout << "3. Exit" << std::endl;
    std::cout << "Choose an option: ";
}

void runServer(const std::string& device_id, const std::string& device_name, int tcp_port) {
    std::cout << "\n[SERVER MODE]" << std::endl;
    std::cout << "Device ID: " << device_id << std::endl;
    std::cout << "Device Name: " << device_name << std::endl;
    std::cout << "TCP Port: " << tcp_port << std::endl;
    std::cout << "Discovery Port: " << DISCOVERY_PORT << std::endl;
    
    // Start UDP broadcaster
    UdpBroadcaster broadcaster(device_id, device_name, tcp_port);
    if (!broadcaster.start()) {
        std::cerr << "Failed to start UDP broadcaster" << std::endl;
        return;
    }
    std::cout << "\n✓ UDP Broadcaster started on port " << DISCOVERY_PORT << std::endl;
    
    // Start TCP server
    TcpServer server(tcp_port);
    if (!server.start([&device_name](SOCKET client_sock, const std::string& client_ip) {
        std::cout << "\n[CONNECTION] Client connected from: " << client_ip << std::endl;
        
        // Send welcome message
        std::string welcome = JsonHelper::createResponseMessage("connected", 
            "Welcome to " + device_name);
        TcpServer::sendJson(client_sock, welcome);
        
        // Handle client messages
        while (true) {
            std::string message = TcpServer::receiveJson(client_sock);
            if (message.empty()) {
                std::cout << "[CONNECTION] Client " << client_ip << " disconnected" << std::endl;
                break;
            }
            
            std::cout << "[RECEIVED] From " << client_ip << ": " << message << std::endl;
            
            // Parse and respond
            std::string type = JsonHelper::parseField(message, "type");
            if (type == "data") {
                std::string content = JsonHelper::parseField(message, "content");
                std::string response = JsonHelper::createResponseMessage("ok", 
                    "Received: " + content);
                TcpServer::sendJson(client_sock, response);
            }
        }
    })) {
        std::cerr << "Failed to start TCP server" << std::endl;
        broadcaster.stop();
        return;
    }
    std::cout << "✓ TCP Server started on port " << tcp_port << std::endl;
    
    std::cout << "\n[SERVER] Running... Press Enter to stop" << std::endl;
    std::cin.get();
    
    std::cout << "\n[SERVER] Shutting down..." << std::endl;
    server.stop();
    broadcaster.stop();
    std::cout << "[SERVER] Stopped" << std::endl;
}

void runClient() {
    std::cout << "\n[CLIENT MODE]" << std::endl;
    std::cout << "Listening for devices on port " << DISCOVERY_PORT << "..." << std::endl;
    
    DeviceRegistry registry;
    
    // Start UDP listener
    UdpListener listener;
    if (!listener.start([&registry](const DeviceInfo& device) {
        registry.addDevice(device);
        std::cout << "\n[DISCOVERED] Device found:" << std::endl;
        std::cout << "  ID: " << device.device_id << std::endl;
        std::cout << "  Name: " << device.device_name << std::endl;
        std::cout << "  IP: " << device.ip_address << std::endl;
        std::cout << "  TCP Port: " << device.tcp_port << std::endl;
    })) {
        std::cerr << "Failed to start UDP listener" << std::endl;
        return;
    }
    std::cout << "✓ UDP Listener started" << std::endl;
    
    std::cout << "\nScanning for 10 seconds..." << std::endl;
    std::this_thread::sleep_for(std::chrono::seconds(10));
    
    auto devices = registry.getDevices();
    
    if (devices.empty()) {
        std::cout << "\n[CLIENT] No devices discovered" << std::endl;
        listener.stop();
        return;
    }
    
    std::cout << "\n[CLIENT] Found " << devices.size() << " device(s)" << std::endl;
    std::cout << "\nSelect a device to connect:" << std::endl;
    
    for (size_t i = 0; i < devices.size(); i++) {
        std::cout << (i + 1) << ". " << devices[i].device_name 
                  << " (" << devices[i].ip_address << ":" << devices[i].tcp_port << ")" << std::endl;
    }
    
    std::cout << "\nEnter device number (or 0 to cancel): ";
    int choice;
    std::cin >> choice;
    std::cin.ignore(); // Clear newline
    
    if (choice < 1 || choice > static_cast<int>(devices.size())) {
        std::cout << "[CLIENT] Cancelled" << std::endl;
        listener.stop();
        return;
    }
    
    const DeviceInfo& selected = devices[choice - 1];
    
    // Connect to selected device
    std::cout << "\n[CLIENT] Connecting to " << selected.device_name 
              << " at " << selected.ip_address << ":" << selected.tcp_port << std::endl;
    
    TcpClient client;
    if (!client.connect(selected.ip_address, selected.tcp_port)) {
        std::cerr << "[CLIENT] Failed to connect" << std::endl;
        listener.stop();
        return;
    }
    std::cout << "✓ Connected successfully" << std::endl;
    
    // Receive welcome message
    std::string welcome = client.receiveJson();
    if (!welcome.empty()) {
        std::string message = JsonHelper::parseField(welcome, "message");
        std::cout << "[SERVER SAYS] " << message << std::endl;
    }
    
    // Interactive communication
    std::cout << "\n[CLIENT] Enter messages to send (type 'quit' to exit):" << std::endl;
    
    while (true) {
        std::cout << "> ";
        std::string input;
        std::getline(std::cin, input);
        
        if (input == "quit" || input == "exit") {
            break;
        }
        
        if (input.empty()) {
            continue;
        }
        
        // Send message
        std::string message = JsonHelper::createDataMessage(input);
        if (!client.sendJson(message)) {
            std::cerr << "[ERROR] Failed to send message" << std::endl;
            break;
        }
        
        // Receive response
        std::string response = client.receiveJson();
        if (response.empty()) {
            std::cerr << "[ERROR] Connection lost" << std::endl;
            break;
        }
        
        std::string status = JsonHelper::parseField(response, "status");
        std::string reply = JsonHelper::parseField(response, "message");
        std::cout << "[RESPONSE] Status: " << status << ", Message: " << reply << std::endl;
    }
    
    std::cout << "\n[CLIENT] Disconnecting..." << std::endl;
    client.disconnect();
    listener.stop();
    std::cout << "[CLIENT] Stopped" << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "LAN Auto-Discovery Demo" << std::endl;
    std::cout << "UDP Broadcast on Port " << DISCOVERY_PORT << std::endl;
    std::cout << "TCP Communication with JSON Format" << std::endl;
    std::cout << "========================================" << std::endl;
    
    printMenu();
    
    int choice;
    std::cin >> choice;
    std::cin.ignore(); // Clear newline
    
    switch (choice) {
        case 1: {
            // Server mode
            std::cout << "\nEnter device name: ";
            std::string device_name;
            std::getline(std::cin, device_name);
            
            std::cout << "Enter TCP port (default 9000): ";
            std::string port_str;
            std::getline(std::cin, port_str);
            int tcp_port = port_str.empty() ? 9000 : std::stoi(port_str);
            
            // Generate device ID based on timestamp
            auto now = std::chrono::system_clock::now().time_since_epoch().count();
            std::string device_id = "device_" + std::to_string(now);
            
            runServer(device_id, device_name, tcp_port);
            break;
        }
        case 2: {
            // Client mode
            runClient();
            break;
        }
        case 3:
            std::cout << "Goodbye!" << std::endl;
            break;
        default:
            std::cout << "Invalid choice" << std::endl;
            break;
    }
    
    return 0;
}
