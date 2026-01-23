#ifndef CPU_H
#define CPU_H

#include <stdbool.h>
#include <stdint.h>

#define MEM_SIZE 65536

typedef struct {
  uint8_t a;      // Accumulator
  uint8_t x;      // Index Register X
  uint8_t y;      // Index Register Y
  uint8_t sp;     // Stack Pointer
  uint16_t pc;    // Program Counter
  uint8_t status; // Status Register (NV-BDIZC)

  uint8_t memory[MEM_SIZE];
  void (*write_callback)(uint16_t addr, uint8_t data);

  // Debugging state
  int last_read_addr;
  int last_write_addr;
  uint64_t instruction_counts[256];
} CPU;

void cpu_reset(CPU *cpu);
uint8_t cpu_read(CPU *cpu, uint16_t addr);
void cpu_write(CPU *cpu, uint16_t addr, uint8_t data);
int cpu_step(CPU *cpu);
void cpu_irq(CPU *cpu);
void cpu_nmi(CPU *cpu);

#endif