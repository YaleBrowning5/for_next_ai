#ifndef NETWORK_DISCOVERY_HPP
#define NETWORK_DISCOVERY_HPP

#include <string>
#include <vector>
#include <functional>
#include <memory>
#include <thread>
#include <atomic>
#include <mutex>
#include <map>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef int socklen_t;
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <fcntl.h>
    #define SOCKET int
    #define INVALID_SOCKET -1
    #define SOCKET_ERROR -1
    #define closesocket close
#endif

namespace network {

// Constants
const int DISCOVERY_PORT = 8866;
const int BUFFER_SIZE = 4096;

// Device information structure
struct DeviceInfo {
    std::string device_id;
    std::string device_name;
    std::string ip_address;
    int tcp_port;
    long long last_seen;
};

// JSON utility functions
class JsonHelper {
public:
    // Simple JSON builder (basic implementation without external library)
    static std::string createDiscoveryMessage(const std::string& device_id, 
                                             const std::string& device_name,
                                             int tcp_port) {
        return "{\"type\":\"discovery\",\"device_id\":\"" + device_id + 
               "\",\"device_name\":\"" + device_name + 
               "\",\"tcp_port\":" + std::to_string(tcp_port) + "}";
    }
    
    static std::string createDataMessage(const std::string& data) {
        return "{\"type\":\"data\",\"content\":\"" + escapeJson(data) + "\"}";
    }
    
    static std::string createResponseMessage(const std::string& status, 
                                            const std::string& message) {
        return "{\"type\":\"response\",\"status\":\"" + status + 
               "\",\"message\":\"" + escapeJson(message) + "\"}";
    }
    
    // Simple JSON parser for specific fields
    static std::string parseField(const std::string& json, const std::string& field) {
        std::string searchStr = "\"" + field + "\":";
        size_t pos = json.find(searchStr);
        if (pos == std::string::npos) return "";
        
        pos += searchStr.length();
        while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\t')) pos++;
        
        if (pos >= json.length()) return "";
        
        if (json[pos] == '"') {
            // String value
            pos++;
            size_t end = json.find('"', pos);
            if (end == std::string::npos) return "";
            return json.substr(pos, end - pos);
        } else {
            // Number value
            size_t end = pos;
            while (end < json.length() && 
                   (isdigit(json[end]) || json[end] == '.' || json[end] == '-')) {
                end++;
            }
            return json.substr(pos, end - pos);
        }
    }

private:
    static std::string escapeJson(const std::string& str) {
        std::string result;
        for (char c : str) {
            switch (c) {
                case '"': result += "\\\""; break;
                case '\\': result += "\\\\"; break;
                case '\n': result += "\\n"; break;
                case '\r': result += "\\r"; break;
                case '\t': result += "\\t"; break;
                default: result += c; break;
            }
        }
        return result;
    }
};

// UDP Broadcaster class - sends discovery messages
class UdpBroadcaster {
public:
    UdpBroadcaster(const std::string& device_id, const std::string& device_name, int tcp_port)
        : device_id_(device_id), device_name_(device_name), tcp_port_(tcp_port),
          running_(false), sock_(INVALID_SOCKET) {
    }
    
    ~UdpBroadcaster() {
        stop();
    }
    
    bool start() {
        if (running_) return false;
        
        // Initialize socket
#ifdef _WIN32
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            return false;
        }
#endif
        
        sock_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (sock_ == INVALID_SOCKET) {
            return false;
        }
        
        // Enable broadcast
        int broadcast = 1;
        if (setsockopt(sock_, SOL_SOCKET, SO_BROADCAST, 
                       (char*)&broadcast, sizeof(broadcast)) == SOCKET_ERROR) {
            closesocket(sock_);
            return false;
        }
        
        running_ = true;
        broadcast_thread_ = std::thread(&UdpBroadcaster::broadcastLoop, this);
        
        return true;
    }
    
    void stop() {
        if (!running_) return;
        running_ = false;
        if (broadcast_thread_.joinable()) {
            broadcast_thread_.join();
        }
        if (sock_ != INVALID_SOCKET) {
            closesocket(sock_);
            sock_ = INVALID_SOCKET;
        }
#ifdef _WIN32
        WSACleanup();
#endif
    }

private:
    void broadcastLoop() {
        sockaddr_in broadcast_addr;
        broadcast_addr.sin_family = AF_INET;
        broadcast_addr.sin_port = htons(DISCOVERY_PORT);
        broadcast_addr.sin_addr.s_addr = INADDR_BROADCAST;
        
        std::string message = JsonHelper::createDiscoveryMessage(
            device_id_, device_name_, tcp_port_);
        
        while (running_) {
            sendto(sock_, message.c_str(), message.length(), 0,
                   (sockaddr*)&broadcast_addr, sizeof(broadcast_addr));
            
            // Broadcast every 5 seconds
            std::this_thread::sleep_for(std::chrono::seconds(5));
        }
    }
    
    std::string device_id_;
    std::string device_name_;
    int tcp_port_;
    std::atomic<bool> running_;
    SOCKET sock_;
    std::thread broadcast_thread_;
};

// UDP Listener class - receives discovery messages
class UdpListener {
public:
    using DiscoveryCallback = std::function<void(const DeviceInfo&)>;
    
    UdpListener() : running_(false), sock_(INVALID_SOCKET) {}
    
    ~UdpListener() {
        stop();
    }
    
    bool start(DiscoveryCallback callback) {
        if (running_) return false;
        
        callback_ = callback;
        
        // Initialize socket
#ifdef _WIN32
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            return false;
        }
#endif
        
        sock_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (sock_ == INVALID_SOCKET) {
            return false;
        }
        
        // Set socket options
        int reuse = 1;
        setsockopt(sock_, SOL_SOCKET, SO_REUSEADDR, (char*)&reuse, sizeof(reuse));
        
        // Bind to discovery port
        sockaddr_in listen_addr;
        listen_addr.sin_family = AF_INET;
        listen_addr.sin_port = htons(DISCOVERY_PORT);
        listen_addr.sin_addr.s_addr = INADDR_ANY;
        
        if (bind(sock_, (sockaddr*)&listen_addr, sizeof(listen_addr)) == SOCKET_ERROR) {
            closesocket(sock_);
            return false;
        }
        
        running_ = true;
        listen_thread_ = std::thread(&UdpListener::listenLoop, this);
        
        return true;
    }
    
    void stop() {
        if (!running_) return;
        running_ = false;
        if (listen_thread_.joinable()) {
            listen_thread_.join();
        }
        if (sock_ != INVALID_SOCKET) {
            closesocket(sock_);
            sock_ = INVALID_SOCKET;
        }
#ifdef _WIN32
        WSACleanup();
#endif
    }

private:
    void listenLoop() {
        char buffer[BUFFER_SIZE];
        sockaddr_in sender_addr;
        socklen_t sender_len = sizeof(sender_addr);
        
        while (running_) {
            int recv_len = recvfrom(sock_, buffer, BUFFER_SIZE - 1, 0,
                                   (sockaddr*)&sender_addr, &sender_len);
            
            if (recv_len > 0) {
                buffer[recv_len] = '\0';
                std::string message(buffer);
                
                // Parse JSON message
                DeviceInfo device;
                device.device_id = JsonHelper::parseField(message, "device_id");
                device.device_name = JsonHelper::parseField(message, "device_name");
                device.ip_address = inet_ntoa(sender_addr.sin_addr);
                
                std::string port_str = JsonHelper::parseField(message, "tcp_port");
                device.tcp_port = port_str.empty() ? 0 : std::stoi(port_str);
                device.last_seen = std::chrono::system_clock::now().time_since_epoch().count();
                
                if (!device.device_id.empty() && device.tcp_port > 0) {
                    if (callback_) {
                        callback_(device);
                    }
                }
            }
        }
    }
    
    std::atomic<bool> running_;
    SOCKET sock_;
    std::thread listen_thread_;
    DiscoveryCallback callback_;
};

// TCP Server class
class TcpServer {
public:
    using ConnectionCallback = std::function<void(SOCKET, const std::string&)>;
    
    TcpServer(int port) : port_(port), running_(false), server_sock_(INVALID_SOCKET) {}
    
    ~TcpServer() {
        stop();
    }
    
    bool start(ConnectionCallback callback) {
        if (running_) return false;
        
        callback_ = callback;
        
#ifdef _WIN32
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            return false;
        }
#endif
        
        server_sock_ = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (server_sock_ == INVALID_SOCKET) {
            return false;
        }
        
        int reuse = 1;
        setsockopt(server_sock_, SOL_SOCKET, SO_REUSEADDR, (char*)&reuse, sizeof(reuse));
        
        sockaddr_in server_addr;
        server_addr.sin_family = AF_INET;
        server_addr.sin_port = htons(port_);
        server_addr.sin_addr.s_addr = INADDR_ANY;
        
        if (bind(server_sock_, (sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
            closesocket(server_sock_);
            return false;
        }
        
        if (listen(server_sock_, 5) == SOCKET_ERROR) {
            closesocket(server_sock_);
            return false;
        }
        
        running_ = true;
        accept_thread_ = std::thread(&TcpServer::acceptLoop, this);
        
        return true;
    }
    
    void stop() {
        if (!running_) return;
        running_ = false;
        if (accept_thread_.joinable()) {
            accept_thread_.join();
        }
        if (server_sock_ != INVALID_SOCKET) {
            closesocket(server_sock_);
            server_sock_ = INVALID_SOCKET;
        }
#ifdef _WIN32
        WSACleanup();
#endif
    }
    
    static bool sendJson(SOCKET sock, const std::string& json_message) {
        int sent = send(sock, json_message.c_str(), json_message.length(), 0);
        return sent > 0;
    }
    
    static std::string receiveJson(SOCKET sock) {
        char buffer[BUFFER_SIZE];
        int recv_len = recv(sock, buffer, BUFFER_SIZE - 1, 0);
        if (recv_len > 0) {
            buffer[recv_len] = '\0';
            return std::string(buffer);
        }
        return "";
    }

private:
    void acceptLoop() {
        while (running_) {
            sockaddr_in client_addr;
            socklen_t client_len = sizeof(client_addr);
            
            SOCKET client_sock = accept(server_sock_, (sockaddr*)&client_addr, &client_len);
            
            if (client_sock != INVALID_SOCKET) {
                std::string client_ip = inet_ntoa(client_addr.sin_addr);
                
                // Handle client in a new thread
                std::thread([this, client_sock, client_ip]() {
                    if (callback_) {
                        callback_(client_sock, client_ip);
                    }
                    closesocket(client_sock);
                }).detach();
            }
        }
    }
    
    int port_;
    std::atomic<bool> running_;
    SOCKET server_sock_;
    std::thread accept_thread_;
    ConnectionCallback callback_;
};

// TCP Client class
class TcpClient {
public:
    TcpClient() : sock_(INVALID_SOCKET) {}
    
    ~TcpClient() {
        disconnect();
    }
    
    bool connect(const std::string& ip_address, int port) {
#ifdef _WIN32
        WSADATA wsaData;
        if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
            return false;
        }
#endif
        
        sock_ = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (sock_ == INVALID_SOCKET) {
            return false;
        }
        
        sockaddr_in server_addr;
        server_addr.sin_family = AF_INET;
        server_addr.sin_port = htons(port);
        inet_pton(AF_INET, ip_address.c_str(), &server_addr.sin_addr);
        
        if (::connect(sock_, (sockaddr*)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
            closesocket(sock_);
            sock_ = INVALID_SOCKET;
            return false;
        }
        
        return true;
    }
    
    void disconnect() {
        if (sock_ != INVALID_SOCKET) {
            closesocket(sock_);
            sock_ = INVALID_SOCKET;
        }
#ifdef _WIN32
        WSACleanup();
#endif
    }
    
    bool sendJson(const std::string& json_message) {
        if (sock_ == INVALID_SOCKET) return false;
        int sent = send(sock_, json_message.c_str(), json_message.length(), 0);
        return sent > 0;
    }
    
    std::string receiveJson() {
        if (sock_ == INVALID_SOCKET) return "";
        
        char buffer[BUFFER_SIZE];
        int recv_len = recv(sock_, buffer, BUFFER_SIZE - 1, 0);
        if (recv_len > 0) {
            buffer[recv_len] = '\0';
            return std::string(buffer);
        }
        return "";
    }
    
    bool isConnected() const {
        return sock_ != INVALID_SOCKET;
    }

private:
    SOCKET sock_;
};

} // namespace network

#endif // NETWORK_DISCOVERY_HPP
