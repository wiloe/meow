cmake_minimum_required(VERSION 3.11)
project(emu6502 C)

set(CMAKE_C_STANDARD 99)

# Suppress MSVC deprecation warnings for standard C functions (fopen, strcpy, etc.)
add_compile_definitions(_CRT_SECURE_NO_WARNINGS)

# --- Raylib Source Build Configuration ---
# Disable building examples and games to speed up compilation
set(BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(BUILD_GAMES    OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE) # Force static build

# Use FetchContent to download and build Raylib automatically
include(FetchContent)
FetchContent_Declare(
    raylib
    GIT_REPOSITORY https://github.com/raysan5/raylib.git
    GIT_TAG        master
)
FetchContent_MakeAvailable(raylib)

add_executable(emu6502 main.c cpu.c)

if(WIN32)
    # Link against the 'raylib' target defined by add_subdirectory
    target_link_libraries(emu6502 PRIVATE raylib gdi32 winmm user32 shell32)
endif()