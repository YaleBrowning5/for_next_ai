#include <iostream>
#include <string>

// Define default values if not provided via CMake
#ifndef VERSION
#define VERSION "unknown"
#endif

#ifndef DEBUG_MODE
#define DEBUG_MODE "OFF"
#endif

#ifndef ENABLE_LOGGING
#define ENABLE_LOGGING "false"
#endif

// Helper macro to convert to string
#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "C++ Example Project" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    
    // Display macro definitions
    std::cout << "Configuration:" << std::endl;
    std::cout << "  VERSION: " << TOSTRING(VERSION) << std::endl;
    std::cout << "  DEBUG_MODE: " << TOSTRING(DEBUG_MODE) << std::endl;
    std::cout << "  ENABLE_LOGGING: " << TOSTRING(ENABLE_LOGGING) << std::endl;
    std::cout << std::endl;
    
    // Display compiler information
    std::cout << "Compiler Information:" << std::endl;
    #ifdef __GNUC__
        std::cout << "  Compiler: GCC " << __GNUC__ << "." << __GNUC_MINOR__ << "." << __GNUC_PATCHLEVEL__ << std::endl;
    #elif defined(__clang__)
        std::cout << "  Compiler: Clang " << __clang_major__ << "." << __clang_minor__ << "." << __clang_patchlevel__ << std::endl;
    #elif defined(_MSC_VER)
        std::cout << "  Compiler: MSVC " << _MSC_VER << std::endl;
    #else
        std::cout << "  Compiler: Unknown" << std::endl;
    #endif
    
    std::cout << "  C++ Standard: " << __cplusplus << std::endl;
    std::cout << std::endl;
    
    // Basic functionality
    std::cout << "Functionality Demo:" << std::endl;
    std::string message = "Hello from C++ example project!";
    std::cout << "  Message: " << message << std::endl;
    
    // Conditional behavior based on debug mode
    std::string debug_mode_str = TOSTRING(DEBUG_MODE);
    if (debug_mode_str == "ON" || debug_mode_str == "true") {
        std::cout << "  [DEBUG] Debug mode is enabled" << std::endl;
    }
    
    // Conditional behavior based on logging
    std::string logging_str = TOSTRING(ENABLE_LOGGING);
    if (logging_str == "true" || logging_str == "ON") {
        std::cout << "  [LOG] Logging is enabled" << std::endl;
    }
    
    std::cout << std::endl;
    std::cout << "Program completed successfully!" << std::endl;
    
    return 0;
}
