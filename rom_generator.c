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

  // 1. Initialize Animation Counter (Zero Page )
  // LDA #
  memory[pc++] = 0xA9;
  memory[pc++] = 0x00;
  // STA
  memory[pc++] = 0x85;
  memory[pc++] = 0x00;

  // LoopStart:
  uint16_t loop_start = pc;

  // 2. Inner Loop: Fill Video Memory (-FF)
  // LDX #
  memory[pc++] = 0xA2;
  memory[pc++] = 0x00;

  // FillLoop:
  uint16_t fill_loop = pc;

  // TXA (Transfer X to A)
  memory[pc++] = 0x8A;
  // ADC  (Add animation counter to create shifting pattern)
  memory[pc++] = 0x65;
  memory[pc++] = 0x00;

  // STA , X (Write to 1st quarter of screen)
  memory[pc++] = 0x9D;
  memory[pc++] = 0x00;
  memory[pc++] = 0x20;
  // STA , X (Write to 2nd quarter)
  memory[pc++] = 0x9D;
  memory[pc++] = 0x00;
  memory[pc++] = 0x21;
  // STA , X (Write to 3rd quarter)
  memory[pc++] = 0x9D;
  memory[pc++] = 0x00;
  memory[pc++] = 0x22;
  // STA , X (Write to 4th quarter)
  memory[pc++] = 0x9D;
  memory[pc++] = 0x00;
  memory[pc++] = 0x23;

  // INX
  memory[pc++] = 0xE8;
  // BNE FillLoop (Loop until X wraps back to 0)
  memory[pc++] = 0xD0;
  memory[pc++] = (uint8_t)(fill_loop - (pc + 1));

  // 3. Update Animation Counter
  // INC
  memory[pc++] = 0xE6;
  memory[pc++] = 0x00;

  // --- Sound Effect ---
  // Set Volume to $40 (approx 25%)
  // LDA #$40
  memory[pc++] = 0xA9;
  memory[pc++] = 0x40;
  // STA $E003
  memory[pc++] = 0x8D;
  memory[pc++] = 0x03;
  memory[pc++] = 0xE0;

  // Set Frequency Low Byte from Animation Counter ($00)
  // LDA $00
  memory[pc++] = 0xA5;
  memory[pc++] = 0x00;
  // STA $E001
  memory[pc++] = 0x8D;
  memory[pc++] = 0x01;
  memory[pc++] = 0xE0;

  // Set Frequency High Byte to $01 (Base freq ~256Hz)
  // LDA #$01
  memory[pc++] = 0xA9;
  memory[pc++] = 0x01;
  // STA $E002
  memory[pc++] = 0x8D;
  memory[pc++] = 0x02;
  memory[pc++] = 0xE0;

  // 4. Infinite Loop
  // JMP LoopStart
  memory[pc++] = 0x4C;
  memory[pc++] = loop_start & 0xFF;
  memory[pc++] = (loop_start >> 8) & 0xFF;

  // --- Reset Vector ---
  // The 6502 reads address - on startup to know where to begin.
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
