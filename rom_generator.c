#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// --- Assembler Helpers ---
uint8_t memory[65536];
uint16_t pc = 0x8000;

void emit(uint8_t b) { memory[pc++] = b; }
void emit_w(uint16_t w) {
  emit(w & 0xFF);
  emit(w >> 8);
}
void emit_rel(int offset) { emit((uint8_t)offset); }

// Opcodes (Mini Assembler)
void LDA_IMM(uint8_t v) {
  emit(0xA9);
  emit(v);
}
void STA_ZP(uint8_t v) {
  emit(0x85);
  emit(v);
}
void LDX_IMM(uint8_t v) {
  emit(0xA2);
  emit(v);
}
void TXA() { emit(0x8A); }
void ADC_ZP(uint8_t v) {
  emit(0x65);
  emit(v);
}
void STA_ABSX(uint16_t v) {
  emit(0x9D);
  emit_w(v);
}
void INX() { emit(0xE8); }
void BNE(int8_t off) {
  emit(0xD0);
  emit_rel(off);
}
void INC_ZP(uint8_t v) {
  emit(0xE6);
  emit(v);
}
void JMP_ABS(uint16_t v) {
  emit(0x4C);
  emit_w(v);
}

int main() {
  // Clear memory to 0
  memset(memory, 0, sizeof(memory));

  // --- 6502 Assembly Program ---
  // Start Address: $8000
  pc = 0x8000;
  uint16_t start_addr = pc;

  // 1. Initialize Animation Counter (Zero Page $00)
  LDA_IMM(0x00);
  STA_ZP(0x00);

  // LoopStart:
  uint16_t loop_start = pc;

  // 2. Inner Loop: Fill Video Memory ($2000-$23FF)
  LDX_IMM(0x00);

  // FillLoop:
  uint16_t fill_loop = pc;

  TXA();
  ADC_ZP(0x00); // Add animation counter to create shifting pattern

  // Write to 4 quarters of screen
  STA_ABSX(0x2000);
  STA_ABSX(0x2100);
  STA_ABSX(0x2200);
  STA_ABSX(0x2300);

  INX();
  BNE(fill_loop - (pc + 2)); // Loop until X wraps back to 0

  // 3. Update Animation Counter
  INC_ZP(0x00);

  // 4. Infinite Loop
  JMP_ABS(loop_start);

  // --- Reset Vector ---
  // The 6502 reads address $FFFC-$FFFD on startup to know where to begin.
  memory[0xFFFC] = start_addr & 0xFF;
  memory[0xFFFD] = (start_addr >> 8) & 0xFF;

  // Write to file
  FILE *f = fopen("rom.bin", "wb");
  if (f) {
    fwrite(memory, 1, sizeof(memory), f);
    fclose(f);
    printf("Success: rom.bin created!\n");
  } else {
    perror("Error: Could not write rom.bin");
    return 1;
  }

  return 0;
}
