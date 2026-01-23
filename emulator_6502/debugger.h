#ifndef DEBUGGER_H
#define DEBUGGER_H

#include "cpu.h"
#include <stdint.h>


int GetInstructionLength(uint8_t opcode);
const char *Disassemble(CPU *cpu, uint16_t addr);
void SimpleAssemble(CPU *cpu, const char *source);

#endif