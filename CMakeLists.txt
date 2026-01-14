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

# --- ROM Generator ---
add_executable(rom_gen rom_generator.c)

# Run the generator to create rom.bin in the source directory
add_custom_command(
    OUTPUT "${CMAKE_SOURCE_DIR}/rom.bin"
    COMMAND $<TARGET_FILE:rom_gen>
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    DEPENDS rom_gen
    COMMENT "Generating rom.bin"
)
add_custom_target(gen_rom_file ALL DEPENDS "${CMAKE_SOURCE_DIR}/rom.bin")

add_executable(emu6502 main.c cpu.c)

if(WIN32)
    # Link against the 'raylib' target defined by add_subdirectory
    target_link_libraries(emu6502 PRIVATE raylib gdi32 winmm user32 shell32)
endif()

add_dependencies(emu6502 gen_rom_file)

# Copy rom.bin to the build directory after build
add_custom_command(TARGET emu6502 POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
    "${CMAKE_SOURCE_DIR}/rom.bin"
    "$<TARGET_FILE_DIR:emu6502>"
    COMMENT "Copying rom.bin to output directory"
)