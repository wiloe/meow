cmake_minimum_required(VERSION 3.14)
project(meow C)

set(CMAKE_C_STANDARD 99)

# Suppress MSVC CRT secure warnings
add_compile_definitions(_CRT_SECURE_NO_WARNINGS)

include(FetchContent)

# --- Raylib ---
FetchContent_Declare(
    raylib
    GIT_REPOSITORY https://github.com/raysan5/raylib.git
    GIT_TAG master
)
FetchContent_MakeAvailable(raylib)

# Suppress warnings for raylib (external dependency)
if(TARGET raylib)
    if(CMAKE_C_COMPILER_ID MATCHES "GNU" OR CMAKE_C_COMPILER_ID MATCHES "Clang")
        target_compile_options(raylib PRIVATE 
            -Wno-tautological-compare 
            -Wno-deprecated-declarations 
            -Wno-unused-function
        )
    endif()
endif()

# --- Icon Generation ---
add_executable(icon_gen icon_generator.c)

add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/icon.ico
    COMMAND icon_gen
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    DEPENDS icon_gen
    COMMENT "Generating 6502 icon"
)
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/meow.rc "IDI_ICON1 ICON \"icon.ico\"")

# --- Main Emulator Target ---
add_executable(meow
    main.c
    cpu.c
    debugger.c
    ${CMAKE_CURRENT_BINARY_DIR}/meow.rc
    ${CMAKE_CURRENT_BINARY_DIR}/icon.ico
)

# Include current directory for header files (cpu.h, debugger.h, etc.)
target_include_directories(meow PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_BINARY_DIR})

# Link Raylib
target_link_libraries(meow PRIVATE raylib)

# Windows-specific dependencies for Raylib
if(WIN32)
    target_link_libraries(meow PRIVATE opengl32 gdi32 winmm)
endif()

# --- ROM Generator Target ---
# Only add if source exists to prevent cmake errors
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/rom_generator.c")
add_executable(rom_generator rom_generator.c)
endif()