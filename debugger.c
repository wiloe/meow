#include "debugger.h"
#include "raylib.h"
#include <stdio.h>
#include <string.h>

int GetInstructionLength(uint8_t opcode) {
  switch (opcode) {
  case 0x0A:
  case 0x4A:
  case 0x2A:
  case 0x6A: // Acc shifts
  case 0x60: // RTS
  case 0xBA:
  case 0xA8: // TAY
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
  case 0x65: // ADC ZP
  case 0xE5: // SBC ZP
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
  case 0x3C: // NOP Abs,X (Illegal)
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
  case 0xA8:
    return "TAY";
  case 0x8A:
    return "TXA";
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
  case 0x65:
    return TextFormat("ADC $%02X", operand);
  case 0x69:
    return TextFormat("ADC #$%02X", operand);
  case 0xE5:
    return TextFormat("SBC $%02X", operand);
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
  case 0x3C:
    return TextFormat("NOP $%04X,X", (operand2 << 8) | operand);
  default:
    return TextFormat("??? ($%02X)", opcode);
  }
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
      unsigned int val = 0;
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