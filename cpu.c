#include "cpu.h"
#include <string.h>

// Status Flags
#define FLAG_C 0x01 // Carry
#define FLAG_Z 0x02 // Zero
#define FLAG_I 0x04 // Interrupt Disable
#define FLAG_D 0x08 // Decimal Mode
#define FLAG_B 0x10 // Break Command
#define FLAG_V 0x40 // Overflow
#define FLAG_N 0x80 // Negative

static uint8_t cpu_fetch(CPU *cpu) {
  uint8_t data = cpu_read(cpu, cpu->pc);
  cpu->pc++;
  return data;
}

static void cpu_set_zn_flags(CPU *cpu, uint8_t value) {
  if (value == 0)
    cpu->status |= FLAG_Z;
  else
    cpu->status &= ~FLAG_Z;

  if (value & 0x80)
    cpu->status |= FLAG_N;
  else
    cpu->status &= ~FLAG_N;
}

static void cpu_compare(CPU *cpu, uint8_t reg, uint8_t val) {
  if (reg >= val)
    cpu->status |= FLAG_C;
  else
    cpu->status &= ~FLAG_C;
  cpu_set_zn_flags(cpu, reg - val);
}

void cpu_write(CPU *cpu, uint16_t addr, uint8_t data) {
  cpu->last_write_addr = (int)addr;
  if (cpu->write_callback) {
    cpu->write_callback(addr, data);
  }

  // Prevent writing to ROM (assuming ROM starts at 0x8000)
  if (addr < 0x8000) {
    cpu->memory[addr] = data;
  }
}

static void cpu_push(CPU *cpu, uint8_t value) {
  cpu_write(cpu, 0x0100 + cpu->sp, value);
  cpu->sp--;
}

static uint8_t cpu_pop(CPU *cpu) {
  cpu->sp++;
  return cpu_read(cpu, 0x0100 + cpu->sp);
}

uint8_t cpu_read(CPU *cpu, uint16_t addr) {
  cpu->last_read_addr = (int)addr;
  return cpu->memory[addr];
}

void cpu_reset(CPU *cpu) {
  cpu->sp = 0xFF;
  cpu->a = 0;
  cpu->x = 0;
  cpu->y = 0;
  cpu->status = 0 | FLAG_I; // Interrupts are disabled on reset

  cpu->last_read_addr = -1;
  cpu->last_write_addr = -1;
  memset(cpu->instruction_counts, 0, sizeof(cpu->instruction_counts));

  // Load PC from Reset Vector ($FFFC-$FFFD)
  uint8_t lo = cpu_read(cpu, 0xFFFC);
  uint8_t hi = cpu_read(cpu, 0xFFFD);
  cpu->pc = (hi << 8) | lo;
}

void cpu_irq(CPU *cpu) {
  if (!(cpu->status & FLAG_I)) {
    cpu_push(cpu, (cpu->pc >> 8) & 0xFF);
    cpu_push(cpu, cpu->pc & 0xFF);
    cpu_push(cpu, cpu->status & ~FLAG_B); // B flag clear for IRQ
    cpu->status |= FLAG_I;

    uint8_t l = cpu_read(cpu, 0xFFFE);
    uint8_t h = cpu_read(cpu, 0xFFFF);
    cpu->pc = (h << 8) | l;
  }
}

void cpu_nmi(CPU *cpu) {
  cpu_push(cpu, (cpu->pc >> 8) & 0xFF);
  cpu_push(cpu, cpu->pc & 0xFF);
  cpu_push(cpu, cpu->status & ~FLAG_B); // B flag clear for NMI
  cpu->status |= FLAG_I;

  uint8_t l = cpu_read(cpu, 0xFFFA);
  uint8_t h = cpu_read(cpu, 0xFFFB);
  cpu->pc = (h << 8) | l;
}

// Basic 6502 Cycle Table (Base cycles)
static const uint8_t CYCLES[256] = {
    7, 6, 0, 0, 0, 3, 5, 0, 3, 2, 2, 0, 0, 4, 6, 0, // 00-0F
    2, 5, 0, 0, 0, 4, 6, 0, 2, 4, 0, 0, 0, 4, 7, 0, // 10-1F
    6, 6, 0, 0, 3, 3, 5, 0, 4, 2, 2, 0, 4, 4, 6, 0, // 20-2F
    2, 5, 0, 0, 0, 4, 6, 0, 2, 4, 0, 0, 0, 4, 7, 0, // 30-3F
    6, 6, 0, 0, 0, 3, 5, 0, 3, 2, 2, 0, 3, 4, 6, 0, // 40-4F
    2, 5, 0, 0, 0, 4, 6, 0, 2, 4, 0, 0, 0, 4, 7, 0, // 50-5F
    6, 6, 0, 0, 0, 3, 5, 0, 4, 2, 2, 0, 5, 4, 6, 0, // 60-6F
    2, 5, 0, 0, 0, 4, 6, 0, 2, 4, 0, 0, 0, 4, 7, 0, // 70-7F
    0, 6, 0, 0, 3, 3, 3, 0, 2, 0, 2, 0, 4, 4, 4, 0, // 80-8F
    2, 6, 0, 0, 4, 4, 4, 0, 2, 5, 2, 0, 0, 5, 0, 0, // 90-9F
    2, 6, 2, 0, 3, 3, 3, 0, 2, 2, 2, 0, 4, 4, 4, 0, // A0-AF
    2, 5, 0, 0, 4, 4, 4, 0, 2, 4, 2, 0, 4, 4, 4, 0, // B0-BF
    2, 6, 0, 0, 3, 3, 5, 0, 2, 2, 2, 0, 4, 4, 6, 0, // C0-CF
    2, 5, 0, 0, 0, 4, 6, 0, 2, 4, 0, 0, 0, 4, 7, 0, // D0-DF
    2, 6, 0, 0, 3, 3, 5, 0, 2, 2, 2, 0, 4, 4, 6, 0, // E0-EF
    2, 5, 0, 0, 0, 4, 6, 0, 2, 4, 0, 0, 0, 4, 7, 0  // F0-FF
};

int cpu_step(CPU *cpu) {
  uint8_t opcode = cpu_fetch(cpu);
  cpu->instruction_counts[opcode]++;
  int cycles = CYCLES[opcode];
  if (cycles == 0) {
    cycles = 2; // Fallback for unimplemented opcodes to prevent infinite loops
  }

  switch (opcode) {
  case 0x00:   // BRK
    cpu->pc++; // Skip padding byte
    cpu_push(cpu, (cpu->pc >> 8) & 0xFF);
    cpu_push(cpu, cpu->pc & 0xFF);
    cpu_push(cpu, cpu->status | FLAG_B); // B flag set for BRK
    cpu->status |= FLAG_I;

    uint8_t l = cpu_read(cpu, 0xFFFE);
    uint8_t h = cpu_read(cpu, 0xFFFF);
    cpu->pc = (h << 8) | l;
    break;
  case 0xA9: // LDA Immediate
    cpu->a = cpu_fetch(cpu);
    cpu_set_zn_flags(cpu, cpu->a);
    break;
  case 0xA5: // LDA Zero Page
    cpu->a = cpu_read(cpu, cpu_fetch(cpu));
    cpu_set_zn_flags(cpu, cpu->a);
    break;
  case 0xB5: // LDA Zero Page, X
    cpu->a = cpu_read(cpu, (cpu_fetch(cpu) + cpu->x) & 0xFF);
    cpu_set_zn_flags(cpu, cpu->a);
    break;
  case 0xAD: // LDA Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu->a = cpu_read(cpu, (h << 8) | l);
    cpu_set_zn_flags(cpu, cpu->a);
  } break;
  case 0xBD: // LDA Absolute, X
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu->a = cpu_read(cpu, ((h << 8) | l) + cpu->x);
    cpu_set_zn_flags(cpu, cpu->a);
  } break;
  case 0xB9: // LDA Absolute, Y
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu->a = cpu_read(cpu, ((h << 8) | l) + cpu->y);
    cpu_set_zn_flags(cpu, cpu->a);
  } break;
  case 0xA1: // LDA (Indirect, X)
  {
    uint8_t zp = (cpu_fetch(cpu) + cpu->x) & 0xFF;
    uint16_t addr = cpu_read(cpu, zp) | (cpu_read(cpu, (zp + 1) & 0xFF) << 8);
    cpu->a = cpu_read(cpu, addr);
    cpu_set_zn_flags(cpu, cpu->a);
  } break;
  case 0xB1: // LDA (Indirect), Y
  {
    uint8_t zp = cpu_fetch(cpu);
    uint16_t base = cpu_read(cpu, zp) | (cpu_read(cpu, (zp + 1) & 0xFF) << 8);
    cpu->a = cpu_read(cpu, base + cpu->y);
    cpu_set_zn_flags(cpu, cpu->a);
  } break;
  case 0xA2: // LDX Immediate
    cpu->x = cpu_fetch(cpu);
    cpu_set_zn_flags(cpu, cpu->x);
    break;
  case 0xA6: // LDX Zero Page
    cpu->x = cpu_read(cpu, cpu_fetch(cpu));
    cpu_set_zn_flags(cpu, cpu->x);
    break;
  case 0xB6: // LDX Zero Page, Y
    cpu->x = cpu_read(cpu, (cpu_fetch(cpu) + cpu->y) & 0xFF);
    cpu_set_zn_flags(cpu, cpu->x);
    break;
  case 0xAE: // LDX Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu->x = cpu_read(cpu, (h << 8) | l);
    cpu_set_zn_flags(cpu, cpu->x);
  } break;
  case 0xBE: // LDX Absolute, Y
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu->x = cpu_read(cpu, ((h << 8) | l) + cpu->y);
    cpu_set_zn_flags(cpu, cpu->x);
  } break;
  case 0xA0: // LDY Immediate
    cpu->y = cpu_fetch(cpu);
    cpu_set_zn_flags(cpu, cpu->y);
    break;
  case 0xA4: // LDY Zero Page
    cpu->y = cpu_read(cpu, cpu_fetch(cpu));
    cpu_set_zn_flags(cpu, cpu->y);
    break;
  case 0xB4: // LDY Zero Page, X
    cpu->y = cpu_read(cpu, (cpu_fetch(cpu) + cpu->x) & 0xFF);
    cpu_set_zn_flags(cpu, cpu->y);
    break;
  case 0xAC: // LDY Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu->y = cpu_read(cpu, (h << 8) | l);
    cpu_set_zn_flags(cpu, cpu->y);
  } break;
  case 0xBC: // LDY Absolute, X
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu->y = cpu_read(cpu, ((h << 8) | l) + cpu->x);
    cpu_set_zn_flags(cpu, cpu->y);
  } break;
  case 0x85: // STA Zero Page
    cpu_write(cpu, cpu_fetch(cpu), cpu->a);
    break;
  case 0x95: // STA Zero Page, X
    cpu_write(cpu, (cpu_fetch(cpu) + cpu->x) & 0xFF, cpu->a);
    break;
  case 0x8D: // STA Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu_write(cpu, (h << 8) | l, cpu->a);
  } break;
  case 0x9D: // STA Absolute, X
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu_write(cpu, ((h << 8) | l) + cpu->x, cpu->a);
  } break;
  case 0x99: // STA Absolute, Y
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu_write(cpu, ((h << 8) | l) + cpu->y, cpu->a);
  } break;
  case 0x81: // STA (Indirect, X)
  {
    uint8_t zp = (cpu_fetch(cpu) + cpu->x) & 0xFF;
    uint16_t addr = cpu_read(cpu, zp) | (cpu_read(cpu, (zp + 1) & 0xFF) << 8);
    cpu_write(cpu, addr, cpu->a);
  } break;
  case 0x91: // STA (Indirect), Y
  {
    uint8_t zp = cpu_fetch(cpu);
    uint16_t base = cpu_read(cpu, zp) | (cpu_read(cpu, (zp + 1) & 0xFF) << 8);
    cpu_write(cpu, base + cpu->y, cpu->a);
  } break;
  case 0x86: // STX Zero Page
    cpu_write(cpu, cpu_fetch(cpu), cpu->x);
    break;
  case 0x96: // STX Zero Page, Y
    cpu_write(cpu, (cpu_fetch(cpu) + cpu->y) & 0xFF, cpu->x);
    break;
  case 0x8E: // STX Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu_write(cpu, (h << 8) | l, cpu->x);
  } break;
  case 0x84: // STY Zero Page
    cpu_write(cpu, cpu_fetch(cpu), cpu->y);
    break;
  case 0x94: // STY Zero Page, X
    cpu_write(cpu, (cpu_fetch(cpu) + cpu->x) & 0xFF, cpu->y);
    break;
  case 0x8C: // STY Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu_write(cpu, (h << 8) | l, cpu->y);
  } break;
  case 0xBA: // TSX
    cpu->x = cpu->sp;
    cpu_set_zn_flags(cpu, cpu->x);
    break;
  case 0x9A: // TXS
    cpu->sp = cpu->x;
    break;
  case 0x48: // PHA
    cpu_push(cpu, cpu->a);
    break;
  case 0x08: // PHP
    cpu_push(cpu, cpu->status | FLAG_B | 0x20);
    break;
  case 0x68: // PLA
    cpu->a = cpu_pop(cpu);
    cpu_set_zn_flags(cpu, cpu->a);
    break;
  case 0x28: // PLP
    cpu->status = cpu_pop(cpu);
    cpu->status &= ~FLAG_B;
    cpu->status |= 0x20;
    break;
  case 0xD0: // BNE (Branch on Result Not Zero)
  {
    int8_t offset = (int8_t)cpu_fetch(cpu);
    if (!(cpu->status & FLAG_Z))
      cpu->pc += offset;
  } break;
  case 0xF0: // BEQ (Branch on Result Zero)
  {
    int8_t offset = (int8_t)cpu_fetch(cpu);
    if (cpu->status & FLAG_Z)
      cpu->pc += offset;
  } break;
  case 0x10: // BPL (Branch on Result Plus)
  {
    int8_t offset = (int8_t)cpu_fetch(cpu);
    if (!(cpu->status & FLAG_N))
      cpu->pc += offset;
  } break;
  case 0x30: // BMI (Branch on Result Minus)
  {
    int8_t offset = (int8_t)cpu_fetch(cpu);
    if (cpu->status & FLAG_N)
      cpu->pc += offset;
  } break;
  case 0x69: // ADC Immediate
  {
    uint8_t value = cpu_fetch(cpu);
    if (cpu->status & FLAG_D) {
      uint16_t l = (cpu->a & 0x0F) + (value & 0x0F) + (cpu->status & FLAG_C);
      uint16_t h = (cpu->a >> 4) + (value >> 4) + (l > 9);
      if (l > 9)
        l += 6;
      if (h > 9)
        h += 6;
      if (h > 9)
        cpu->status |= FLAG_C;
      else
        cpu->status &= ~FLAG_C;
      cpu->a = (h << 4) | (l & 0x0F);
      cpu_set_zn_flags(cpu, cpu->a);
    } else {
      uint16_t sum = (uint16_t)cpu->a + value + (cpu->status & FLAG_C);
      if (~((uint16_t)cpu->a ^ value) & ((uint16_t)cpu->a ^ sum) & 0x0080)
        cpu->status |= FLAG_V;
      else
        cpu->status &= ~FLAG_V;
      if (sum > 0xFF)
        cpu->status |= FLAG_C;
      else
        cpu->status &= ~FLAG_C;
      cpu->a = (uint8_t)sum;
      cpu_set_zn_flags(cpu, cpu->a);
    }
  } break;
  case 0xE9: // SBC Immediate
  {
    uint8_t value = cpu_fetch(cpu);
    if (cpu->status & FLAG_D) {
      uint16_t l =
          (cpu->a & 0x0F) - (value & 0x0F) - (1 - (cpu->status & FLAG_C));
      uint16_t h = (cpu->a >> 4) - (value >> 4) - ((l & 0x10) != 0);
      if (l & 0x10)
        l -= 6;
      if (h & 0x10)
        h -= 6;
      if (h & 0x10)
        cpu->status &= ~FLAG_C;
      else
        cpu->status |= FLAG_C;
      cpu->a = (h << 4) | (l & 0x0F);
      cpu_set_zn_flags(cpu, cpu->a);
    } else {
      value = value ^ 0xFF;
      uint16_t sum = (uint16_t)cpu->a + value + (cpu->status & FLAG_C);
      if (~((uint16_t)cpu->a ^ value) & ((uint16_t)cpu->a ^ sum) & 0x0080)
        cpu->status |= FLAG_V;
      else
        cpu->status &= ~FLAG_V;
      if (sum > 0xFF)
        cpu->status |= FLAG_C;
      else
        cpu->status &= ~FLAG_C;
      cpu->a = (uint8_t)sum;
      cpu_set_zn_flags(cpu, cpu->a);
    }
  } break;
  case 0x29: // AND Immediate
    cpu->a &= cpu_fetch(cpu);
    cpu_set_zn_flags(cpu, cpu->a);
    break;
  case 0x09: // ORA Immediate
    cpu->a |= cpu_fetch(cpu);
    cpu_set_zn_flags(cpu, cpu->a);
    break;
  case 0x49: // EOR Immediate
    cpu->a ^= cpu_fetch(cpu);
    cpu_set_zn_flags(cpu, cpu->a);
    break;
  case 0xE6: // INC Zero Page
  {
    uint8_t addr = cpu_fetch(cpu);
    cpu_write(cpu, addr, cpu_read(cpu, addr) + 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr)); // Note: reads back from memory
  } break;
  case 0xEE: // INC Absolute
  {
    uint8_t low = cpu_fetch(cpu);
    uint8_t high = cpu_fetch(cpu);
    uint16_t addr = (high << 8) | low;
    cpu_write(cpu, addr, cpu_read(cpu, addr) + 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr)); // Note: reads back from memory
  } break;
  case 0xC6: // DEC Zero Page
  {
    uint8_t addr = cpu_fetch(cpu);
    cpu_write(cpu, addr, cpu_read(cpu, addr) - 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr)); // Note: reads back from memory
  } break;
  case 0xCE: // DEC Absolute
  {
    uint8_t low = cpu_fetch(cpu);
    uint8_t high = cpu_fetch(cpu);
    uint16_t addr = (high << 8) | low;
    cpu_write(cpu, addr, cpu_read(cpu, addr) - 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr)); // Note: reads back from memory
  } break;
  case 0xE8: // INX
    cpu->x++;
    cpu_set_zn_flags(cpu, cpu->x);
    break;
  case 0xCA: // DEX
    cpu->x--;
    cpu_set_zn_flags(cpu, cpu->x);
    break;
  case 0xC8: // INY
    cpu->y++;
    cpu_set_zn_flags(cpu, cpu->y);
    break;
  case 0x88: // DEY
    cpu->y--;
    cpu_set_zn_flags(cpu, cpu->y);
    break;
  case 0x4C: // JMP Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu->pc = (h << 8) | l;
  } break;
  case 0x6C: // JMP Indirect
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t ptr = (h << 8) | l;
    // Note: 6502 bug (page boundary wrapping) not implemented for simplicity
    uint16_t target = cpu_read(cpu, ptr) | (cpu_read(cpu, ptr + 1) << 8);
    cpu->pc = target;
  } break;
  case 0x20: // JSR Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t target = (h << 8) | l;
    uint16_t ret = cpu->pc - 1;
    cpu_push(cpu, (ret >> 8) & 0xFF);
    cpu_push(cpu, ret & 0xFF);
    cpu->pc = target;
  } break;
  case 0x60: // RTS
  {
    uint8_t l = cpu_pop(cpu);
    uint8_t h = cpu_pop(cpu);
    cpu->pc = ((h << 8) | l) + 1;
  } break;
  // --- ASL (Arithmetic Shift Left) ---
  case 0x0A: // ASL Accumulator
  {
    uint16_t val = (uint16_t)cpu->a << 1;
    if (val & 0x100)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu->a = (uint8_t)val;
    cpu_set_zn_flags(cpu, cpu->a);
  } break;
  case 0x06: // ASL Zero Page
  {
    uint8_t addr = cpu_fetch(cpu);
    uint16_t val = (uint16_t)cpu_read(cpu, addr) << 1;
    if (val & 0x100)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, (uint8_t)val);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0x16: // ASL Zero Page, X
  {
    uint8_t addr = (cpu_fetch(cpu) + cpu->x) & 0xFF;
    uint16_t val = (uint16_t)cpu_read(cpu, addr) << 1;
    if (val & 0x100)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, (uint8_t)val);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0x0E: // ASL Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t addr = (h << 8) | l;
    uint16_t val = (uint16_t)cpu_read(cpu, addr) << 1;
    if (val & 0x100)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, (uint8_t)val);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0x1E: // ASL Absolute, X
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t addr = ((h << 8) | l) + cpu->x;
    uint16_t val = (uint16_t)cpu_read(cpu, addr) << 1;
    if (val & 0x100)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, (uint8_t)val);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  // --- LSR (Logical Shift Right) ---
  case 0x4A: // LSR Accumulator
  {
    if (cpu->a & 0x01)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu->a >>= 1;
    cpu_set_zn_flags(cpu, cpu->a);
  } break;
  case 0x46: // LSR Zero Page
  {
    uint8_t addr = cpu_fetch(cpu);
    uint8_t val = cpu_read(cpu, addr);
    if (val & 0x01)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, val >> 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0x56: // LSR Zero Page, X
  {
    uint8_t addr = (cpu_fetch(cpu) + cpu->x) & 0xFF;
    uint8_t val = cpu_read(cpu, addr);
    if (val & 0x01)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, val >> 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0x4E: // LSR Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t addr = (h << 8) | l;
    uint8_t val = cpu_read(cpu, addr);
    if (val & 0x01)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, val >> 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0x5E: // LSR Absolute, X
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t addr = ((h << 8) | l) + cpu->x;
    uint8_t val = cpu_read(cpu, addr);
    if (val & 0x01)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, val >> 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  // --- ROL (Rotate Left) ---
  case 0x2A: // ROL Accumulator
  {
    uint16_t val = ((uint16_t)cpu->a << 1) | (cpu->status & FLAG_C);
    if (val & 0x100)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu->a = (uint8_t)val;
    cpu_set_zn_flags(cpu, cpu->a);
  } break;
  case 0x26: // ROL Zero Page
  {
    uint8_t addr = cpu_fetch(cpu);
    uint16_t val =
        ((uint16_t)cpu_read(cpu, addr) << 1) | (cpu->status & FLAG_C);
    if (val & 0x100)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, (uint8_t)val);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0x36: // ROL Zero Page, X
  {
    uint8_t addr = (cpu_fetch(cpu) + cpu->x) & 0xFF;
    uint16_t val =
        ((uint16_t)cpu_read(cpu, addr) << 1) | (cpu->status & FLAG_C);
    if (val & 0x100)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, (uint8_t)val);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0x2E: // ROL Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t addr = (h << 8) | l;
    uint16_t val =
        ((uint16_t)cpu_read(cpu, addr) << 1) | (cpu->status & FLAG_C);
    if (val & 0x100)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, (uint8_t)val);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0x3E: // ROL Absolute, X
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t addr = ((h << 8) | l) + cpu->x;
    uint16_t val =
        ((uint16_t)cpu_read(cpu, addr) << 1) | (cpu->status & FLAG_C);
    if (val & 0x100)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_write(cpu, addr, (uint8_t)val);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  // --- ROR (Rotate Right) ---
  case 0x6A: // ROR Accumulator
  {
    uint8_t c = cpu->a & 0x01;
    cpu->a = (cpu->a >> 1) | ((cpu->status & FLAG_C) << 7);
    if (c)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_set_zn_flags(cpu, cpu->a);
  } break;
  case 0x66: // ROR Zero Page
  {
    uint8_t addr = cpu_fetch(cpu);
    uint8_t val = cpu_read(cpu, addr);
    uint8_t c = val & 0x01;
    val = (val >> 1) | ((cpu->status & FLAG_C) << 7);
    cpu->memory[addr] = val;
    if (c)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_set_zn_flags(cpu, val);
  } break;
  case 0x76: // ROR Zero Page, X
  {
    uint8_t addr = (cpu_fetch(cpu) + cpu->x) & 0xFF;
    uint8_t val = cpu_read(cpu, addr);
    uint8_t c = val & 0x01;
    val = (val >> 1) | ((cpu->status & FLAG_C) << 7);
    cpu->memory[addr] = val;
    if (c)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_set_zn_flags(cpu, val);
  } break;
  case 0x6E: // ROR Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t addr = (h << 8) | l;
    uint8_t val = cpu_read(cpu, addr);
    uint8_t c = val & 0x01;
    val = (val >> 1) | ((cpu->status & FLAG_C) << 7);
    cpu->memory[addr] = val;
    if (c)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_set_zn_flags(cpu, val);
  } break;
  case 0x7E: // ROR Absolute, X
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t addr = ((h << 8) | l) + cpu->x;
    uint8_t val = cpu_read(cpu, addr);
    uint8_t c = val & 0x01;
    val = (val >> 1) | ((cpu->status & FLAG_C) << 7);
    cpu->memory[addr] = val;
    if (c)
      cpu->status |= FLAG_C;
    else
      cpu->status &= ~FLAG_C;
    cpu_set_zn_flags(cpu, val);
  } break;
  // --- CMP (Compare Accumulator) ---
  case 0xC9: // CMP Immediate
    cpu_compare(cpu, cpu->a, cpu_fetch(cpu));
    break;
  case 0xC5: // CMP Zero Page
    cpu_compare(cpu, cpu->a, cpu_read(cpu, cpu_fetch(cpu)));
    break;
  case 0xD5: // CMP Zero Page, X
    cpu_compare(cpu, cpu->a, cpu_read(cpu, (cpu_fetch(cpu) + cpu->x) & 0xFF));
    break;
  case 0xCD: // CMP Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu_compare(cpu, cpu->a, cpu_read(cpu, (h << 8) | l));
  } break;
  case 0xDD: // CMP Absolute, X
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu_compare(cpu, cpu->a, cpu_read(cpu, ((h << 8) | l) + cpu->x));
  } break;
  case 0xD9: // CMP Absolute, Y
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu_compare(cpu, cpu->a, cpu_read(cpu, ((h << 8) | l) + cpu->y));
  } break;
  case 0xC1: // CMP (Indirect, X)
  {
    uint8_t zp = (cpu_fetch(cpu) + cpu->x) & 0xFF;
    uint16_t addr = cpu_read(cpu, zp) | (cpu_read(cpu, (zp + 1) & 0xFF) << 8);
    cpu_compare(cpu, cpu->a, cpu_read(cpu, addr));
  } break;
  case 0xD1: // CMP (Indirect), Y
  {
    uint8_t zp = cpu_fetch(cpu);
    uint16_t base = cpu_read(cpu, zp) | (cpu_read(cpu, (zp + 1) & 0xFF) << 8);
    cpu_compare(cpu, cpu->a, cpu_read(cpu, base + cpu->y));
  } break;
  // --- CPX (Compare X Register) ---
  case 0xE0: // CPX Immediate
    cpu_compare(cpu, cpu->x, cpu_fetch(cpu));
    break;
  case 0xE4: // CPX Zero Page
    cpu_compare(cpu, cpu->x, cpu_read(cpu, cpu_fetch(cpu)));
    break;
  case 0xEC: // CPX Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu_compare(cpu, cpu->x, cpu_read(cpu, (h << 8) | l));
  } break;
  // --- CPY (Compare Y Register) ---
  case 0xC0: // CPY Immediate
    cpu_compare(cpu, cpu->y, cpu_fetch(cpu));
    break;
  case 0xC4: // CPY Zero Page
    cpu_compare(cpu, cpu->y, cpu_read(cpu, cpu_fetch(cpu)));
    break;
  case 0xCC: // CPY Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    cpu_compare(cpu, cpu->y, cpu_read(cpu, (h << 8) | l));
  } break;
  // --- BIT (Bit Test) ---
  case 0x24: // BIT Zero Page
  {
    uint8_t val = cpu_read(cpu, cpu_fetch(cpu));
    if ((cpu->a & val) == 0)
      cpu->status |= FLAG_Z;
    else
      cpu->status &= ~FLAG_Z;
    cpu->status =
        (cpu->status & 0x3F) | (val & 0xC0); // Copy bits 6 and 7 to V and N
  } break;
  case 0x2C: // BIT Absolute
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint8_t val = cpu_read(cpu, (h << 8) | l);
    if ((cpu->a & val) == 0)
      cpu->status |= FLAG_Z;
    else
      cpu->status &= ~FLAG_Z;
    cpu->status =
        (cpu->status & 0x3F) | (val & 0xC0); // Copy bits 6 and 7 to V and N
  } break;
  // --- Flag Manipulation ---
  case 0x18:
    cpu->status &= ~FLAG_C;
    break; // CLC
  case 0x38:
    cpu->status |= FLAG_C;
    break; // SEC
  case 0x58:
    cpu->status &= ~FLAG_I;
    break; // CLI
  case 0x78:
    cpu->status |= FLAG_I;
    break; // SEI
  case 0xB8:
    cpu->status &= ~FLAG_V;
    break; // CLV
  case 0xD8:
    cpu->status &= ~FLAG_D;
    break; // CLD
  case 0xF8:
    cpu->status |= FLAG_D;
    break; // SED
  // --- Branches ---
  case 0x90: // BCC
  {
    int8_t offset = (int8_t)cpu_fetch(cpu);
    if (!(cpu->status & FLAG_C))
      cpu->pc += offset;
  } break;
  case 0xB0: // BCS
  {
    int8_t offset = (int8_t)cpu_fetch(cpu);
    if (cpu->status & FLAG_C)
      cpu->pc += offset;
  } break;
  case 0x50: // BVC
  {
    int8_t offset = (int8_t)cpu_fetch(cpu);
    if (!(cpu->status & FLAG_V))
      cpu->pc += offset;
  } break;
  case 0x70: // BVS
  {
    int8_t offset = (int8_t)cpu_fetch(cpu);
    if (cpu->status & FLAG_V)
      cpu->pc += offset;
  } break;
  // --- RTI ---
  case 0x40: // RTI
  {
    cpu->status = cpu_pop(cpu);
    cpu->status &= ~FLAG_B;
    cpu->status |= 0x20;
    uint8_t l = cpu_pop(cpu);
    uint8_t h = cpu_pop(cpu);
    cpu->pc = (h << 8) | l;
  } break;
  // --- INC/DEC Missing Modes ---
  case 0xF6: // INC Zero Page, X
  {
    uint8_t addr = (cpu_fetch(cpu) + cpu->x) & 0xFF;
    cpu_write(cpu, addr, cpu_read(cpu, addr) + 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0xFE: // INC Absolute, X
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t addr = ((h << 8) | l) + cpu->x;
    cpu_write(cpu, addr, cpu_read(cpu, addr) + 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0xD6: // DEC Zero Page, X
  {
    uint8_t addr = (cpu_fetch(cpu) + cpu->x) & 0xFF;
    cpu_write(cpu, addr, cpu_read(cpu, addr) - 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0xDE: // DEC Absolute, X
  {
    uint8_t l = cpu_fetch(cpu);
    uint8_t h = cpu_fetch(cpu);
    uint16_t addr = ((h << 8) | l) + cpu->x;
    cpu_write(cpu, addr, cpu_read(cpu, addr) - 1);
    cpu_set_zn_flags(cpu, cpu_read(cpu, addr));
  } break;
  case 0xEA: // NOP
    break;
  default:
    // Unimplemented opcode
    break;
  }

  return cycles;
}