#include <stdint.h>
#include <stdio.h>
#include <string.h>


int main() {
  uint8_t memory[65536];
  // Clear memory to 0
  memset(memory, 0, sizeof(memory));

  // --- 6502 Assembly Program ---
  // Start Address: $8000
  uint16_t pc = 0x8000;
  uint16_t start_addr = pc;

  // 1. Initialize Animation Counter (Zero Page $00)
  // LDA #$00
  memory[pc++] = 0xA9;
  memory[pc++] = 0x00;
  // STA $00
  memory[pc++] = 0x85;
  memory[pc++] = 0x00;

  // LoopStart:
  uint16_t loop_start = pc;

  // 2. Inner Loop: Fill Video Memory ($2000-$23FF)
  // LDX #$00
  memory[pc++] = 0xA2;
  memory[pc++] = 0x00;

  // FillLoop:
  uint16_t fill_loop = pc;

  // TXA (Transfer X to A)
  memory[pc++] = 0x8A;
  // ADC $00 (Add animation counter to create shifting pattern)
  memory[pc++] = 0x65;
  memory[pc++] = 0x00;

  // STA $2000, X (Write to 1st quarter of screen)
  memory[pc++] = 0x9D;
  memory[pc++] = 0x00;
  memory[pc++] = 0x20;
  // STA $2100, X (Write to 2nd quarter)
  memory[pc++] = 0x9D;
  memory[pc++] = 0x00;
  memory[pc++] = 0x21;
  // STA $2200, X (Write to 3rd quarter)
  memory[pc++] = 0x9D;
  memory[pc++] = 0x00;
  memory[pc++] = 0x22;
  // STA $2300, X (Write to 4th quarter)
  memory[pc++] = 0x9D;
  memory[pc++] = 0x00;
  memory[pc++] = 0x23;

  // INX
  memory[pc++] = 0xE8;
  // BNE FillLoop (Loop until X wraps back to 0)
  memory[pc++] = 0xD0;
  memory[pc++] = (uint8_t)(fill_loop - (pc + 1));

  // 3. Update Animation Counter
  // INC $00
  memory[pc++] = 0xE6;
  memory[pc++] = 0x00;

  // 4. Infinite Loop
  // JMP LoopStart
  memory[pc++] = 0x4C;
  memory[pc++] = loop_start & 0xFF;
  memory[pc++] = (loop_start >> 8) & 0xFF;

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
    printf("Error: Could not write rom.bin\n");
    return 1;
  }

  return 0;
}
