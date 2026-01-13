cmake_minimum_required(VERSION 3.10)
project(emu6502 C)

set(CMAKE_C_STANDARD 99)

add_executable(emu6502 main.c cpu.c)

if(WIN32)
    target_link_libraries(emu6502 raylib gdi32 winmm user32 shell32)
endif()