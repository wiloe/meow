#include "raylib.h"
#include <math.h>   // Required for audio generation
#include <stdio.h>  // Required for fopen, fread
#include <stdlib.h> // Required for strtol
#include <string.h> // Required for strtok, strncpy

#define RAYGUI_IMPLEMENTATION
#include "raygui.h"

#include "cpu.h"

#define SCREEN_WIDTH 800
#define SCREEN_HEIGHT 600

int GetInstructionLength(uint8_t opcode) {
  switch (opcode) {
  case 0x0A:
  case 0x4A:
  case 0x2A:
  case 0x6A: // Acc shifts
  case 0x60: // RTS
  case 0xBA:
  case 0x9A: // TSX, TXS
  case 0x18: // CLC
  case 0x38: // SEC
  case 0x58: // CLI
  case 0x78: // SEI
  case 0xB8: // CLV
  case 0xD8: // CLD
  case 0xF8: // SED
  case 0x40: // RTI
    return 1;
  case 0xA9:
  case 0xA2:
  case 0xA0:
  case 0xD0:
  case 0xF0:
  case 0x10:
  case 0x30:
  case 0x90: // BCC
  case 0xB0: // BCS
  case 0x50: // BVC
  case 0x70: // BVS
  case 0x69:
  case 0xE9:
  case 0x29:
  case 0x09:
  case 0x49:
  case 0xE6:
  case 0xC6:
  case 0xF6: // INC ZP,X
  case 0xD6: // DEC ZP,X
  case 0xA5:
  case 0xB5:
  case 0xA1:
  case 0xB1: // LDA ZP/Ind
  case 0x85:
  case 0x95:
  case 0x81:
  case 0x91: // STA ZP/Ind
  case 0xA6:
  case 0xB6: // LDX ZP
  case 0xA4:
  case 0xB4: // LDY ZP
  case 0x86:
  case 0x96: // STX ZP
  case 0x84:
  case 0x94: // STY ZP
  case 0x06:
  case 0x16:
  case 0x46:
  case 0x56:
  case 0x26:
  case 0x36:
  case 0x66:
  case 0x76: // ZP shifts
  case 0xC9:
  case 0xC5:
  case 0xD5:
  case 0xC1:
  case 0xD1: // CMP
  case 0xE0:
  case 0xE4: // CPX
  case 0xC0:
  case 0xC4: // CPY
  case 0x24: // BIT ZP
    return 2;
  case 0xEE:
  case 0xCE:
  case 0xFE: // INC Abs,X
  case 0xDE: // DEC Abs,X
  case 0xAD:
  case 0xBD:
  case 0xB9: // LDA Abs
  case 0x8D:
  case 0x9D:
  case 0x99: // STA Abs
  case 0xAE:
  case 0xBE: // LDX Abs
  case 0xAC:
  case 0xBC: // LDY Abs
  case 0x8E: // STX Abs
  case 0x8C: // STY Abs
  case 0x4C:
  case 0x6C: // JMP
  case 0x20: // JSR
  case 0x0E:
  case 0x1E:
  case 0x4E:
  case 0x5E:
  case 0x2E:
  case 0x3E:
  case 0x6E:
  case 0x7E: // Abs shifts
  case 0xCD:
  case 0xDD:
  case 0xD9: // CMP Abs
  case 0xEC: // CPX Abs
  case 0xCC: // CPY Abs
  case 0x2C: // BIT Abs
    return 3;
  default:
    return 1;
  }
}

const char *Disassemble(CPU *cpu, uint16_t addr) {
  uint8_t opcode = cpu->memory[addr];
  uint8_t operand = cpu->memory[(addr + 1) & 0xFFFF];
  uint8_t operand2 = cpu->memory[(addr + 2) & 0xFFFF];
  switch (opcode) {
  case 0x00:
    return "BRK";
  case 0xA9:
    return TextFormat("LDA #$%02X", operand);
  case 0xA5:
    return TextFormat("LDA $%02X", operand);
  case 0xB5:
    return TextFormat("LDA $%02X,X", operand);
  case 0xAD:
    return TextFormat("LDA $%04X", (operand2 << 8) | operand);
  case 0xBD:
    return TextFormat("LDA $%04X,X", (operand2 << 8) | operand);
  case 0xB9:
    return TextFormat("LDA $%04X,Y", (operand2 << 8) | operand);
  case 0xA1:
    return TextFormat("LDA ($%02X,X)", operand);
  case 0xB1:
    return TextFormat("LDA ($%02X),Y", operand);
  case 0xA2:
    return TextFormat("LDX #$%02X", operand);
  case 0xA6:
    return TextFormat("LDX $%02X", operand);
  case 0xB6:
    return TextFormat("LDX $%02X,Y", operand);
  case 0xAE:
    return TextFormat("LDX $%04X", (operand2 << 8) | operand);
  case 0xBE:
    return TextFormat("LDX $%04X,Y", (operand2 << 8) | operand);
  case 0xA0:
    return TextFormat("LDY #$%02X", operand);
  case 0xA4:
    return TextFormat("LDY $%02X", operand);
  case 0xB4:
    return TextFormat("LDY $%02X,X", operand);
  case 0xAC:
    return TextFormat("LDY $%04X", (operand2 << 8) | operand);
  case 0xBC:
    return TextFormat("LDY $%04X,X", (operand2 << 8) | operand);
  case 0x85:
    return TextFormat("STA $%02X", operand);
  case 0x95:
    return TextFormat("STA $%02X,X", operand);
  case 0x8D:
    return TextFormat("STA $%04X", (operand2 << 8) | operand);
  case 0x9D:
    return TextFormat("STA $%04X,X", (operand2 << 8) | operand);
  case 0x99:
    return TextFormat("STA $%04X,Y", (operand2 << 8) | operand);
  case 0x81:
    return TextFormat("STA ($%02X,X)", operand);
  case 0x91:
    return TextFormat("STA ($%02X),Y", operand);
  case 0x86:
    return TextFormat("STX $%02X", operand);
  case 0x96:
    return TextFormat("STX $%02X,Y", operand);
  case 0x8E:
    return TextFormat("STX $%04X", (operand2 << 8) | operand);
  case 0x84:
    return TextFormat("STY $%02X", operand);
  case 0x94:
    return TextFormat("STY $%02X,X", operand);
  case 0x8C:
    return TextFormat("STY $%04X", (operand2 << 8) | operand);
  case 0x4C:
    return TextFormat("JMP $%04X", (operand2 << 8) | operand);
  case 0x6C:
    return TextFormat("JMP ($%04X)", (operand2 << 8) | operand);
  case 0x20:
    return TextFormat("JSR $%04X", (operand2 << 8) | operand);
  case 0x60:
    return "RTS";
  case 0xBA:
    return "TSX";
  case 0x9A:
    return "TXS";
  case 0x0A:
    return "ASL A";
  case 0x06:
    return TextFormat("ASL $%02X", operand);
  case 0x16:
    return TextFormat("ASL $%02X,X", operand);
  case 0x0E:
    return TextFormat("ASL $%04X", (operand2 << 8) | operand);
  case 0x1E:
    return TextFormat("ASL $%04X,X", (operand2 << 8) | operand);
  case 0x4A:
    return "LSR A";
  case 0x46:
    return TextFormat("LSR $%02X", operand);
  case 0x56:
    return TextFormat("LSR $%02X,X", operand);
  case 0x4E:
    return TextFormat("LSR $%04X", (operand2 << 8) | operand);
  case 0x5E:
    return TextFormat("LSR $%04X,X", (operand2 << 8) | operand);
  case 0x2A:
    return "ROL A";
  case 0x26:
    return TextFormat("ROL $%02X", operand);
  case 0x36:
    return TextFormat("ROL $%02X,X", operand);
  case 0x2E:
    return TextFormat("ROL $%04X", (operand2 << 8) | operand);
  case 0x3E:
    return TextFormat("ROL $%04X,X", (operand2 << 8) | operand);
  case 0x6A:
    return "ROR A";
  case 0x66:
    return TextFormat("ROR $%02X", operand);
  case 0x76:
    return TextFormat("ROR $%02X,X", operand);
  case 0x6E:
    return TextFormat("ROR $%04X", (operand2 << 8) | operand);
  case 0x7E:
    return TextFormat("ROR $%04X,X", (operand2 << 8) | operand);
  case 0x48:
    return "PHA";
  case 0x08:
    return "PHP";
  case 0x68:
    return "PLA";
  case 0x28:
    return "PLP";
  case 0xD0:
    return TextFormat("BNE $%02X", operand);
  case 0xF0:
    return TextFormat("BEQ $%02X", operand);
  case 0x10:
    return TextFormat("BPL $%02X", operand);
  case 0x30:
    return TextFormat("BMI $%02X", operand);
  case 0x90:
    return TextFormat("BCC $%02X", operand);
  case 0xB0:
    return TextFormat("BCS $%02X", operand);
  case 0x50:
    return TextFormat("BVC $%02X", operand);
  case 0x70:
    return TextFormat("BVS $%02X", operand);
  case 0x69:
    return TextFormat("ADC #$%02X", operand);
  case 0xE9:
    return TextFormat("SBC #$%02X", operand);
  case 0x29:
    return TextFormat("AND #$%02X", operand);
  case 0x09:
    return TextFormat("ORA #$%02X", operand);
  case 0x49:
    return TextFormat("EOR #$%02X", operand);
  case 0xE6:
    return TextFormat("INC $%02X", operand);
  case 0xEE:
    return TextFormat("INC $%04X", (operand2 << 8) | operand);
  case 0xF6:
    return TextFormat("INC $%02X,X", operand);
  case 0xFE:
    return TextFormat("INC $%04X,X", (operand2 << 8) | operand);
  case 0xC6:
    return TextFormat("DEC $%02X", operand);
  case 0xCE:
    return TextFormat("DEC $%04X", (operand2 << 8) | operand);
  case 0xD6:
    return TextFormat("DEC $%02X,X", operand);
  case 0xDE:
    return TextFormat("DEC $%04X,X", (operand2 << 8) | operand);
  case 0xE8:
    return "INX";
  case 0xCA:
    return "DEX";
  case 0xC8:
    return "INY";
  case 0x88:
    return "DEY";
  case 0x18:
    return "CLC";
  case 0x38:
    return "SEC";
  case 0x58:
    return "CLI";
  case 0x78:
    return "SEI";
  case 0xB8:
    return "CLV";
  case 0xD8:
    return "CLD";
  case 0xF8:
    return "SED";
  case 0x40:
    return "RTI";
  case 0xEA:
    return "NOP";
  default:
    return TextFormat("??? ($%02X)", opcode);
  }
}

// Console Log State
char consoleBuffer[4096] = {0};
int consoleIndex = 0;

// ROM Write Warning State
bool showRomWriteWarning = false;
int romWriteWarningTimer = 0;

// Audio State
AudioStream audioStream;
float wavePhase = 0.0f;
volatile float waveFrequency = 440.0f;
volatile float waveVolume = 0.0f;
uint8_t soundRegL = 0;
uint8_t soundRegH = 0;

void AudioInputCallback(void *buffer, unsigned int frames) {
  short *d = (short *)buffer;
  for (unsigned int i = 0; i < frames; i++) {
    if (waveVolume > 0.0f && waveFrequency > 20.0f) {
      // Square wave generation
      float sample = (fmodf(wavePhase, 1.0f) < 0.5f) ? 1.0f : -1.0f;
      d[i] = (short)(sample * waveVolume *
                     16000.0f); // 16000 is roughly half of short max

      wavePhase += waveFrequency / 44100.0f;
      if (wavePhase >= 1.0f)
        wavePhase -= 1.0f;
    } else {
      d[i] = 0;
    }
  }
}

void OnCpuWrite(uint16_t addr, uint8_t data) {
  // Check for invalid ROM writes (excluding MMIO area $E000-$E003)
  if (addr >= 0x8000 && !(addr >= 0xE000 && addr <= 0xE003)) {
    showRomWriteWarning = true;
    romWriteWarningTimer = 60; // Show warning for 60 frames (1 second)
  }

  if (addr == 0xE000) {
    if (consoleIndex < 4095) {
      consoleBuffer[consoleIndex++] = (char)data;
      consoleBuffer[consoleIndex] = 0;
    }
  } else if (addr == 0xE001) {
    soundRegL = data;
    waveFrequency = (float)((soundRegH << 8) | soundRegL);
  } else if (addr == 0xE002) {
    soundRegH = data;
    waveFrequency = (float)((soundRegH << 8) | soundRegL);
  } else if (addr == 0xE003) {
    waveVolume = (float)data / 255.0f;
  }
}

void SaveSnapshot(CPU *cpu, const char *filename) {
  FILE *f = fopen(filename, "wb");
  if (!f)
    return;
  fwrite(cpu, sizeof(CPU), 1, f);
  fclose(f);
}

void LoadSnapshot(CPU *cpu, const char *filename) {
  FILE *f = fopen(filename, "rb");
  if (!f)
    return;
  // Preserve the callback pointer as it's not valid to load from disk
  void (*cb)(uint16_t, uint8_t) = cpu->write_callback;
  fread(cpu, sizeof(CPU), 1, f);
  cpu->write_callback = cb;
  fclose(f);
}

void SimpleAssemble(CPU *cpu, const char *source) {
  char buffer[1024];
  strncpy(buffer, source, sizeof(buffer));
  buffer[sizeof(buffer) - 1] = 0;

  uint16_t pc = 0x0600; // Assemble to $0600

  char *line = strtok(buffer, "\n");
  while (line) {
    char mnemonic[16] = {0};
    char operand[16] = {0};
    int args = sscanf(line, "%s %s", mnemonic, operand);

    if (args > 0) {
      // ToUpper
      for (int i = 0; mnemonic[i]; i++)
        if (mnemonic[i] >= 'a' && mnemonic[i] <= 'z')
          mnemonic[i] -= 32;

      uint8_t opcode = 0;
      int val = 0;
      int len = 0;

      if (strcmp(mnemonic, "LDA") == 0) {
        if (operand[0] == '#') {
          opcode = 0xA9;
          len = 2;
          sscanf(operand, "#$%x", &val);
        } else {
          opcode = 0xAD;
          len = 3;
          sscanf(operand, "$%x", &val);
        }
      } else if (strcmp(mnemonic, "STA") == 0) {
        opcode = 0x8D;
        len = 3;
        sscanf(operand, "$%x", &val);
      } else if (strcmp(mnemonic, "LDX") == 0) {
        if (operand[0] == '#') {
          opcode = 0xA2;
          len = 2;
          sscanf(operand, "#$%x", &val);
        } else {
          opcode = 0xAE;
          len = 3;
          sscanf(operand, "$%x", &val);
        }
      } else if (strcmp(mnemonic, "LDY") == 0) {
        if (operand[0] == '#') {
          opcode = 0xA0;
          len = 2;
          sscanf(operand, "#$%x", &val);
        } else {
          opcode = 0xAC;
          len = 3;
          sscanf(operand, "$%x", &val);
        }
      } else if (strcmp(mnemonic, "JMP") == 0) {
        opcode = 0x4C;
        len = 3;
        sscanf(operand, "$%x", &val);
      } else if (strcmp(mnemonic, "RTS") == 0) {
        opcode = 0x60;
        len = 1;
      } else if (strcmp(mnemonic, "NOP") == 0) {
        opcode = 0xEA;
        len = 1;
      }

      if (opcode) {
        cpu->memory[pc++] = opcode;
        if (len > 1)
          cpu->memory[pc++] = val & 0xFF;
        if (len > 2)
          cpu->memory[pc++] = (val >> 8) & 0xFF;
      }
    }
    line = strtok(NULL, "\n");
  }
}

int main(int argc, char *argv[]) {
  InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT, "6502 Emulator (C + Raylib)");
  SetTargetFPS(60);

  // Initialize Audio
  InitAudioDevice();
  audioStream = LoadAudioStream(44100, 16, 1);
  SetAudioStreamCallback(audioStream, AudioInputCallback);
  PlayAudioStream(audioStream);

  // Initialize 6502 CPU
  CPU cpu;
  memset(cpu.memory, 0, MEM_SIZE); // Clear memory explicitly on startup
  cpu.write_callback = OnCpuWrite;

  // GUI State
  bool showMemory = true;
  int memStart = 0x0000;
  bool editAddrMode = false;
  bool showGraphics = false;

  bool breakpoints[MEM_SIZE] = {0};
  bool runEmulation = false;
  double clockAccumulator = 0.0;
  char addrBuffer[5] = "0000";

  bool editFileMode = false;
  char fileBuffer[64] = "rom.bin";
  char statusMsg[64] = "Ready";

  // CLI Argument Loading
  if (argc > 1) {
    FILE *f = fopen(argv[1], "rb");
    if (f) {
      fread(cpu.memory, 1, MEM_SIZE, f);
      fclose(f);
      snprintf(statusMsg, 64, "Loaded CLI: %s", GetFileName(argv[1]));
      strncpy(fileBuffer, argv[1], 63);
      fileBuffer[63] = '\0';
    } else {
      snprintf(statusMsg, 64, "CLI Load Failed");
    }
  } else {
    // Auto-load rom.bin if it exists
    FILE *f = fopen("rom.bin", "rb");
    if (f) {
      fread(cpu.memory, 1, MEM_SIZE, f);
      fclose(f);
      snprintf(statusMsg, 64, "Auto-Loaded: rom.bin");
    }
  }

  // Reset CPU after loading ROM so it picks up the Reset Vector from the loaded
  // data
  cpu_reset(&cpu);

  // Register Edit State
  char regPcBuf[5] = "0000";
  bool editPc = false;
  char regABuf[3] = "00";
  bool editA = false;
  char regXBuf[3] = "00";
  bool editX = false;
  char regYBuf[3] = "00";
  bool editY = false;
  char regSpBuf[3] = "00";
  bool editSp = false;
  // Status is complex to edit bitwise, skipping for brevity or adding simple
  // hex edit

  // Assembler State
  int bottomTab = 0; // 0: Console, 1: Assembler, 2: Profiler
  char asmSource[1024] = "LDA #$01\nSTA $0200\nRTS";
  bool editAsm = false;

  while (!WindowShouldClose()) {
    // Update
    int cyclesThisFrame = 0;
    if (runEmulation) {
      double frameTime = GetFrameTime();
      if (frameTime > 0.05)
        frameTime = 0.05;                        // Prevent spiral of death
      clockAccumulator += frameTime * 1000000.0; // 1 MHz target

      while (clockAccumulator > 0) {
        if (breakpoints[cpu.pc]) {
          runEmulation = false;
          clockAccumulator = 0;
          break;
        }
        int cycles = cpu_step(&cpu);
        clockAccumulator -= cycles;
        cyclesThisFrame += cycles;
      }
    }

    // Update Timers
    if (romWriteWarningTimer > 0) {
      romWriteWarningTimer--;
      if (romWriteWarningTimer == 0)
        showRomWriteWarning = false;
    }

    // Input Handling (Map ASCII to 0x00FF)
    int key = GetCharPressed();
    if (key > 0 && key < 256) {
      cpu.memory[0x00FF] = (uint8_t)key;
    }

    // Draw
    BeginDrawing();
    ClearBackground(GetColor(GuiGetStyle(DEFAULT, BACKGROUND_COLOR)));

    // --- CPU Status Panel ---
    GuiPanel((Rectangle){10, 10, 220, 200}, "CPU Registers");

    GuiLabel((Rectangle){25, 40, 30, 20}, "PC:");
    if (!editPc)
      snprintf(regPcBuf, 5, "%04X", cpu.pc);
    if (GuiTextBox((Rectangle){55, 40, 60, 20}, regPcBuf, 5, editPc)) {
      editPc = !editPc;
      if (!editPc)
        cpu.pc = (uint16_t)strtol(regPcBuf, NULL, 16);
    }

    GuiLabel((Rectangle){25, 65, 30, 20}, "A:");
    if (!editA)
      snprintf(regABuf, 3, "%02X", cpu.a);
    if (GuiTextBox((Rectangle){55, 65, 40, 20}, regABuf, 3, editA)) {
      editA = !editA;
      if (!editA)
        cpu.a = (uint8_t)strtol(regABuf, NULL, 16);
    }

    GuiLabel((Rectangle){25, 90, 30, 20}, "X:");
    if (!editX)
      snprintf(regXBuf, 3, "%02X", cpu.x);
    if (GuiTextBox((Rectangle){55, 90, 40, 20}, regXBuf, 3, editX)) {
      editX = !editX;
      if (!editX)
        cpu.x = (uint8_t)strtol(regXBuf, NULL, 16);
    }

    GuiLabel((Rectangle){25, 115, 30, 20}, "Y:");
    if (!editY)
      snprintf(regYBuf, 3, "%02X", cpu.y);
    if (GuiTextBox((Rectangle){55, 115, 40, 20}, regYBuf, 3, editY)) {
      editY = !editY;
      if (!editY)
        cpu.y = (uint8_t)strtol(regYBuf, NULL, 16);
    }

    GuiLabel((Rectangle){25, 140, 30, 20}, "SP:");
    if (!editSp)
      snprintf(regSpBuf, 3, "%02X", cpu.sp);
    if (GuiTextBox((Rectangle){55, 140, 40, 20}, regSpBuf, 3, editSp)) {
      editSp = !editSp;
      if (!editSp)
        cpu.sp = (uint8_t)strtol(regSpBuf, NULL, 16);
    }

    // Flags visualization (NV-BDIZC)
    GuiLabel(
        (Rectangle){25, 165, 180, 20},
        TextFormat(
            "Flags: %c%c-%c%c%c%c%c", (cpu.status & 0x80) ? 'N' : '.',
            (cpu.status & 0x40) ? 'V' : '.', (cpu.status & 0x10) ? 'B' : '.',
            (cpu.status & 0x08) ? 'D' : '.', (cpu.status & 0x04) ? 'I' : '.',
            (cpu.status & 0x02) ? 'Z' : '.', (cpu.status & 0x01) ? 'C' : '.'));

    GuiLabel((Rectangle){25, 185, 180, 20},
             TextFormat("FPS: %d  Speed: %.2f MHz", GetFPS(),
                        (float)cyclesThisFrame * GetFPS() / 1000000.0f));

    // --- Controls ---
    if (GuiButton((Rectangle){10, 220, 65, 30}, "Step")) {
      runEmulation = false;
      cpu_step(&cpu);
    }
    if (GuiButton((Rectangle){80, 220, 65, 30},
                  runEmulation ? "Pause" : "Run")) {
      runEmulation = !runEmulation;
    }

    if (GuiButton((Rectangle){150, 220, 65, 30}, "Reset")) {
      runEmulation = false;
      // Reset sound
      soundRegL = 0;
      soundRegH = 0;
      waveFrequency = 0.0f;
      waveVolume = 0.0f;

      // Reload ROM
      FILE *f = fopen(fileBuffer, "rb");
      if (f) {
        fread(cpu.memory, 1, MEM_SIZE, f);
        fclose(f);
        snprintf(statusMsg, 64, "Reset & Reloaded");
      } else {
        snprintf(statusMsg, 64, "Reset (No ROM)");
      }

      // Reset CPU after reloading ROM
      cpu_reset(&cpu);
    }

    GuiLabel((Rectangle){10, 245, 220, 20}, "In:$00FF Snd:$E001 Vid:$2000");

    // --- Disassembly View ---
    GuiPanel((Rectangle){10, 260, 220, 200}, "Disassembly");

    uint16_t pc = cpu.pc;
    for (int i = 0; i < 16; i++) {
      int y = 290 + i * 20;
      if (y > 450)
        break;

      const char *asmStr = Disassemble(&cpu, pc);

      // Breakpoint Toggle
      bool isBp = breakpoints[pc];
      if (GuiCheckBox((Rectangle){10, y, 15, 15}, "", &isBp)) {
        breakpoints[pc] = isBp;
      }

      Color textColor = DARKGRAY;
      if (i == 0) {
        textColor = RED;
      }
      if (breakpoints[pc])
        textColor = BLUE;

      DrawText(TextFormat("$%04X: %s", pc, asmStr), 30, y, 10, textColor);
      pc += GetInstructionLength(cpu.memory[pc]);
    }

    // --- Stack View ---
    GuiPanel((Rectangle){10, 470, 220, 120}, "Stack (Page 1)");
    for (int i = 0; i < 5; i++) {
      uint8_t offset = cpu.sp + i;
      int addr = 0x0100 + offset;
      uint8_t val = cpu.memory[addr];

      Color col = DARKGRAY;
      const char *prefix = "   ";
      if (i == 0) {
        col = RED; // Highlight SP
        prefix = "SP>";
      }
      DrawText(TextFormat("%s $%04X: %02X", prefix, addr, val), 20,
               500 + i * 18, 10, col);
    }

    // --- Memory Hex Editor ---
    GuiPanel((Rectangle){240, 10, 550, 400},
             showGraphics ? "Graphics Mode ($2000)" : "Memory View");

    if (GuiButton((Rectangle){680, 15, 100, 20},
                  showGraphics ? "Show Hex" : "Show Screen")) {
      showGraphics = !showGraphics;
    }

    // Navigation Controls
    if (GuiButton((Rectangle){250, 35, 30, 25}, "<"))
      memStart -= 0x100;
    if (GuiButton((Rectangle){285, 35, 30, 25}, ">"))
      memStart += 0x100;

    GuiLabel((Rectangle){330, 35, 40, 25}, "Addr:");
    if (GuiTextBox((Rectangle){370, 35, 60, 25}, addrBuffer, 5, editAddrMode)) {
      editAddrMode = !editAddrMode;
      if (!editAddrMode) {
        memStart = (int)strtol(addrBuffer, NULL, 16);
        memStart &= 0xFFF0; // Align to 16 bytes
      }
    }

    // Clamp memory address
    if (memStart < 0)
      memStart = 0;
    if (memStart > MEM_SIZE - 1)
      memStart = MEM_SIZE - 1;

    // Draw Hex Grid
    int startY = 110;
    int startX = 250;

    if (showGraphics) {
      int scale = 8;
      int imgX = 240 + (550 - 32 * scale) / 2; // Center in panel

      for (int y = 0; y < 32; y++) {
        for (int x = 0; x < 32; x++) {
          uint8_t val = cpu.memory[0x2000 + y * 32 + x];
          Color col = (Color){val, val, val, 255};
          DrawRectangle(imgX + x * scale, startY + y * scale, scale, scale,
                        col);
        }
      }
      DrawRectangleLines(imgX, startY, 32 * scale, 32 * scale, BLACK);
    } else {
      for (int row = 0; row < 14; row++) {
        int rowAddr = memStart + row * 16;
        if (rowAddr >= MEM_SIZE)
          break;

        DrawText(TextFormat("0x%04X", rowAddr), startX, startY + row * 20, 10,
                 DARKGRAY);

        for (int col = 0; col < 16; col++) {
          int addr = rowAddr + col;
          if (addr >= MEM_SIZE)
            break;

          if (addr == cpu.last_read_addr) {
            DrawRectangle(startX + 48 + col * 20, startY + row * 20, 18, 18,
                          GREEN);
          }
          if (addr == cpu.last_write_addr) {
            DrawRectangle(startX + 48 + col * 20, startY + row * 20, 18, 18,
                          RED);
          }

          unsigned char val = cpu.memory[addr];
          DrawText(TextFormat("%02X", val), startX + 50 + col * 20,
                   startY + row * 20, 10, BLACK);

          // ASCII
          char c = (val >= 32 && val <= 126) ? (char)val : '.';
          DrawText(TextFormat("%c", c), startX + 380 + col * 10,
                   startY + row * 20, 10, DARKGRAY);
        }
      }
    }

    // Draw ROM Write Warning
    if (showRomWriteWarning) {
      DrawText("ROM WRITE ATTEMPT!", 520, 425, 20, RED);
    }

    // --- File Loader ---
    GuiLabel((Rectangle){250, 70, 60, 25}, "Load Bin:");
    if (GuiTextBox((Rectangle){310, 70, 150, 25}, fileBuffer, 64,
                   editFileMode)) {
      editFileMode = !editFileMode;
    }

    if (GuiButton((Rectangle){470, 70, 60, 25}, "Load")) {
      FILE *f = fopen(fileBuffer, "rb");
      if (f) {
        // Load at current memory view address (or fixed 0x0000/0x8000 depending
        // on preference) Here we load at memStart for flexibility
        fread(&cpu.memory[memStart], 1, MEM_SIZE - memStart, f);
        fclose(f);
        snprintf(statusMsg, 64, "Loaded at 0x%04X", memStart);
      } else {
        snprintf(statusMsg, 64, "Failed to open!");
      }
    }
    GuiLabel((Rectangle){540, 70, 200, 25}, statusMsg);

    // --- Snapshots ---
    if (GuiButton((Rectangle){650, 70, 60, 25}, "Save")) {
      SaveSnapshot(&cpu, "snapshot.sav");
      snprintf(statusMsg, 64, "Saved snapshot.sav");
    }
    if (GuiButton((Rectangle){715, 70, 60, 25}, "Load")) {
      LoadSnapshot(&cpu, "snapshot.sav");
      snprintf(statusMsg, 64, "Loaded snapshot.sav");
    }

    // --- Bottom Panel (Console / Assembler) ---
    // Tabs
    if (GuiButton((Rectangle){240, 420, 80, 20}, "Console"))
      bottomTab = 0;
    if (GuiButton((Rectangle){325, 420, 80, 20}, "Assembler"))
      bottomTab = 1;
    if (GuiButton((Rectangle){410, 420, 80, 20}, "Profiler"))
      bottomTab = 2;

    if (bottomTab == 0) {
      GuiPanel((Rectangle){240, 440, 550, 150}, "Console Log ($E000)");
      GuiDrawText(consoleBuffer, (Rectangle){250, 460, 530, 120},
                  TEXT_ALIGN_LEFT, DARKGRAY);
    } else if (bottomTab == 1) {
      GuiPanel((Rectangle){240, 440, 550, 150},
               "Simple Assembler (Start: $0600)");
      if (GuiTextBox((Rectangle){250, 460, 400, 120}, asmSource, 1024,
                     editAsm)) {
        editAsm = !editAsm;
      }
      if (GuiButton((Rectangle){660, 460, 120, 30}, "Compile")) {
        SimpleAssemble(&cpu, asmSource);
        snprintf(statusMsg, 64, "Assembled to $0600");
        cpu.pc = 0x0600; // Auto-jump to start
      }
    } else if (bottomTab == 2) {
      GuiPanel((Rectangle){240, 440, 550, 150}, "Profiler Stats");

      // Calculate stats
      uint64_t totalInstructions = 0;
      for (int i = 0; i < 256; i++) {
        totalInstructions += cpu.instruction_counts[i];
      }

      GuiLabel((Rectangle){250, 460, 200, 20},
               TextFormat("Total Instr: %llu", totalInstructions));
      GuiLabel((Rectangle){450, 460, 200, 20},
               TextFormat("Cycles/Frame: %d", cyclesThisFrame));

      // Find top 5 instructions
      int indices[256];
      for (int i = 0; i < 256; i++)
        indices[i] = i;

      // Simple bubble sort for top 5
      for (int i = 0; i < 5; i++) {
        for (int j = i + 1; j < 256; j++) {
          if (cpu.instruction_counts[indices[j]] >
              cpu.instruction_counts[indices[i]]) {
            int temp = indices[i];
            indices[i] = indices[j];
            indices[j] = temp;
          }
        }
      }

      // Draw Bars
      for (int i = 0; i < 5; i++) {
        int opcode = indices[i];
        uint64_t count = cpu.instruction_counts[opcode];
        if (count == 0)
          break;

        float percentage = (totalInstructions > 0)
                               ? (float)count / (float)totalInstructions
                               : 0.0f;

        DrawRectangle(250, 490 + i * 22, (int)(percentage * 300), 18, BLUE);
        DrawText(TextFormat("$%02X: %llu (%.1f%%)", opcode, count,
                            percentage * 100.0f),
                 255, 490 + i * 22 + 2, 10, WHITE);
      }
    }

    EndDrawing();
  }

  UnloadAudioStream(audioStream);
  CloseAudioDevice();
  CloseWindow();
  return 0;
}