# Compiler
CC = gcc

# Compiler Flags
# -I. ensures headers in the current directory are found
CFLAGS = -Wall -std=c99 -Wno-missing-braces -I.

# Linker Flags (Windows/MinGW)
# Requires raylib to be installed or libraylib.a present in library path
LDFLAGS = -lraylib -lopengl32 -lgdi32 -lwinmm

# Source Files
SRCS = main.c cpu.c debugger.c
OBJS = $(SRCS:.c=.o)

# Output Names
TARGET = meow
GEN_TARGET = rom_generator

# Default Target
all: $(TARGET) $(GEN_TARGET)

# Link Main Emulator
$(TARGET): $(OBJS)
	$(CC) -o $@ $(OBJS) $(LDFLAGS)

# Compile ROM Generator
$(GEN_TARGET): rom_generator.c
	$(CC) -o $@ rom_generator.c

# Compile Source Files to Objects
%.o: %.c
	$(CC) -c $< -o $@ $(CFLAGS)

# Clean Build Artifacts
clean:
	rm -f $(OBJS) $(TARGET).exe $(GEN_TARGET).exe

# Deep clean (removes CMake build directory)
distclean: clean
	rm -rf build

.PHONY: all clean distclean
