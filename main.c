#include "raylib.h"
#include <math.h>   // Required for audio generation
#include <stdio.h>  // Required for fopen, fread
#include <stdlib.h> // Required for strtol
#include <string.h> // Required for strtok, strncpy

#define RAYGUI_IMPLEMENTATION
// #include "raygui.h"
#include "meowgui.h"

#include "cpu.h"
#include "debugger.h"

#define SCREEN_WIDTH 800
#define SCREEN_HEIGHT 600
#define APP_VERSION "0.1.0"

// Simple 16-color palette (C64 style)
static const Color PALETTE[16] = {
    {0, 0, 0, 255},       // 0: Black
    {255, 255, 255, 255}, // 1: White
    {136, 0, 0, 255},     // 2: Red
    {170, 255, 238, 255}, // 3: Cyan
    {204, 68, 204, 255},  // 4: Purple
    {0, 204, 85, 255},    // 5: Green
    {0, 0, 170, 255},     // 6: Blue
    {238, 238, 119, 255}, // 7: Yellow
    {221, 136, 85, 255},  // 8: Orange
    {102, 68, 0, 255},    // 9: Brown
    {255, 119, 119, 255}, // 10: Light Red
    {51, 51, 51, 255},    // 11: Dark Grey
    {119, 119, 119, 255}, // 12: Grey
    {170, 255, 102, 255}, // 13: Light Green
    {0, 136, 255, 255},   // 14: Light Blue
    {187, 187, 187, 255}  // 15: Light Grey
};

// Console Log State
char consoleBuffer[4096] = {0};
int consoleIndex = 0;

// ROM Write Warning State
bool showRomWriteWarning = false;
int romWriteWarningTimer = 0;

// Manual Text
const char *MANUAL_TEXT = "6502 ASSEMBLY MANUAL\n"
                          "--------------------\n\n"
                          "ADDRESSING MODES:\n"
                          "  Immediate:   LDA #$01    (Value 0x01)\n"
                          "  Zero Page:   LDA $01     (Mem 0x0001)\n"
                          "  Absolute:    LDA $0200   (Mem 0x0200)\n"
                          "  Indexed:     LDA $0200,X (Mem 0x0200 + X)\n\n"
                          "COMMON OPCODES:\n"
                          "  LDA/LDX/LDY  Load Register (A, X, Y)\n"
                          "  STA/STX/STY  Store Register (A, X, Y)\n"
                          "  ADC          Add with Carry\n"
                          "  SBC          Subtract with Carry\n"
                          "  INC/DEC      Increment/Decrement\n"
                          "  INX/DEX      Increment/Decrement X\n"
                          "  INY/DEY      Increment/Decrement Y\n"
                          "  JMP          Jump to Address\n"
                          "  JSR          Jump to Subroutine\n"
                          "  RTS          Return from Subroutine\n"
                          "  CMP/CPX/CPY  Compare Register\n"
                          "  BNE          Branch if Not Equal (Z=0)\n"
                          "  BEQ          Branch if Equal (Z=1)\n"
                          "  BCC          Branch if Carry Clear\n"
                          "  BCS          Branch if Carry Set\n";

// --- File Dialog ---
typedef struct {
  bool active;
  char dirPath[512];
  FilePathList files;
  char **displayNames;
  int count;
  int scrollIndex;
  int activeItem;
  int focusItem;
  char selectedPath[512];
  bool fileSelected;
} GuiFileDialogState;

GuiFileDialogState fileDialog = {0};

void InitFileDialog(const char *initDir) {
  fileDialog.active = false;
  strncpy(fileDialog.dirPath, initDir, 511);
  fileDialog.files.count = 0;
  fileDialog.count = 0;
  fileDialog.displayNames = NULL;
}

void RefreshFileList() {
  if (fileDialog.files.count > 0)
    UnloadDirectoryFiles(fileDialog.files);
  if (fileDialog.displayNames) {
    for (int i = 0; i < fileDialog.count; i++)
      free(fileDialog.displayNames[i]);
    free(fileDialog.displayNames);
  }

  if (DirectoryExists(fileDialog.dirPath)) {
    fileDialog.files = LoadDirectoryFiles(fileDialog.dirPath);
    fileDialog.count = fileDialog.files.count;
    fileDialog.displayNames =
        (char **)malloc(fileDialog.count * sizeof(char *));

    for (int i = 0; i < fileDialog.count; i++) {
      const char *name = GetFileName(fileDialog.files.paths[i]);
      bool isDir = DirectoryExists(fileDialog.files.paths[i]);

      fileDialog.displayNames[i] = (char *)malloc(strlen(name) + 2);
      strcpy(fileDialog.displayNames[i], name);
      if (isDir)
        strcat(fileDialog.displayNames[i], "/");
    }
  } else {
    fileDialog.count = 0;
    fileDialog.displayNames = NULL;
  }
  fileDialog.activeItem = -1;
  fileDialog.focusItem = -1;
  fileDialog.scrollIndex = 0;
}

void OpenFileDialog() {
  fileDialog.active = true;
  fileDialog.fileSelected = false;
  RefreshFileList();
}

void CloseFileDialog() {
  fileDialog.active = false;
  if (fileDialog.files.count > 0)
    UnloadDirectoryFiles(fileDialog.files);
  if (fileDialog.displayNames) {
    for (int i = 0; i < fileDialog.count; i++)
      free(fileDialog.displayNames[i]);
    free(fileDialog.displayNames);
    fileDialog.displayNames = NULL;
  }
  fileDialog.count = 0;
}

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

void SetCustomStyle() {
  // Dark Theme Example
  GuiSetStyle(DEFAULT, BACKGROUND_COLOR, (int)0x2D2D2DFF);
  GuiSetStyle(DEFAULT, LINE_COLOR, (int)0x636363FF);
  GuiSetStyle(DEFAULT, TEXT_COLOR_NORMAL, (int)0xDEDEDEFF);
  GuiSetStyle(DEFAULT, TEXT_COLOR_FOCUSED, (int)0x87CFFFFF);
  GuiSetStyle(DEFAULT, TEXT_COLOR_PRESSED, (int)0x0492C7FF);
  GuiSetStyle(DEFAULT, TEXT_COLOR_DISABLED, (int)0x7C7C7CFF);

  GuiSetStyle(DEFAULT, BORDER_COLOR_NORMAL, (int)0x454545FF);
  GuiSetStyle(DEFAULT, BORDER_COLOR_FOCUSED, (int)0x5BB2D9FF);
  GuiSetStyle(DEFAULT, BORDER_COLOR_PRESSED, (int)0x0492C7FF);
  GuiSetStyle(DEFAULT, BORDER_COLOR_DISABLED, (int)0x454545FF);

  GuiSetStyle(DEFAULT, BASE_COLOR_NORMAL, (int)0x454545FF);
  GuiSetStyle(DEFAULT, BASE_COLOR_FOCUSED, (int)0x454545FF);
  GuiSetStyle(DEFAULT, BASE_COLOR_PRESSED, (int)0x323232FF);
  GuiSetStyle(DEFAULT, BASE_COLOR_DISABLED, (int)0x2D2D2DFF);
}

int main(int argc, char *argv[]) {
  SetConfigFlags(FLAG_WINDOW_RESIZABLE | FLAG_MSAA_4X_HINT);
  InitWindow(SCREEN_WIDTH, SCREEN_HEIGHT,
             "6502 Emulator (C + Raylib) v" APP_VERSION);
  MaximizeWindow();
  SetTargetFPS(60);

  // Initialize Audio
  InitAudioDevice();
  audioStream = LoadAudioStream(44100, 16, 1);
  SetAudioStreamCallback(audioStream, AudioInputCallback);
  PlayAudioStream(audioStream);

  // Apply custom style
  SetCustomStyle();

  // Initialize File Dialog
  InitFileDialog(GetWorkingDirectory());

  // Initialize 6502 CPU
  CPU cpu;
  memset(cpu.memory, 0, MEM_SIZE); // Clear memory explicitly on startup
  cpu.write_callback = OnCpuWrite;

  // GUI State
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
      runEmulation = true;
    } else {
      snprintf(statusMsg, 64, "CLI Load Failed");
    }
  } else {
    // Auto-load rom.bin if it exists
    const char *romPath = "rom.bin";
    FILE *f = fopen(romPath, "rb");
    if (!f) {
      romPath = "../rom.bin"; // Try parent directory (common in build folders)
      f = fopen(romPath, "rb");
    }

    if (f) {
      fread(cpu.memory, 1, MEM_SIZE, f);
      fclose(f);
      snprintf(statusMsg, 64, "Auto-Loaded: %s", GetFileName(romPath));
      strncpy(fileBuffer, romPath, 63);
      fileBuffer[63] = '\0';
      runEmulation = true;
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

  // Menu Bar State
  bool menuFileActive = false;
  bool menuEmulationActive = false;
  bool menuHelpActive = false;
  bool showManual = false;

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

    // --- Layout Calculations ---
    float scrW = (float)GetScreenWidth();
    float scrH = (float)GetScreenHeight();
    float margin = 10;
    float menuBarHeight = 30;
    float topY = margin + menuBarHeight; // Shift everything down

    float sidebarW = 220;
    float rightX = margin + sidebarW + margin;
    float rightW = scrW - rightX - margin;
    float bottomH = 180;
    float tabH = 25;
    float mainH = scrH - topY - margin - bottomH - tabH;
    if (mainH < 200)
      mainH = 200; // Minimum height safety

    // --- Menu Bar ---
    GuiPanel((Rectangle){0, 0, scrW, menuBarHeight}, NULL);

    // File Menu
    if (GuiButton((Rectangle){5, 5, 50, 20}, "File")) {
      menuFileActive = !menuFileActive;
      menuEmulationActive = false;
      menuHelpActive = false;
    }

    // Emulation Menu
    if (GuiButton((Rectangle){60, 5, 70, 20}, "Emulation")) {
      menuEmulationActive = !menuEmulationActive;
      menuFileActive = false;
      menuHelpActive = false;
    }

    // Help Menu
    if (GuiButton((Rectangle){135, 5, 50, 20}, "Help")) {
      menuHelpActive = !menuHelpActive;
      menuFileActive = false;
      menuEmulationActive = false;
    }

    // Toolbar Shortcuts
    if (GuiButton((Rectangle){200, 5, 40, 20}, "Reset")) {
      runEmulation = false;
      soundRegL = 0;
      soundRegH = 0;
      waveFrequency = 0.0f;
      waveVolume = 0.0f;
      FILE *f = fopen(fileBuffer, "rb");
      if (f) {
        fread(cpu.memory, 1, MEM_SIZE, f);
        fclose(f);
        snprintf(statusMsg, 64, "Reset & Reloaded");
      } else {
        snprintf(statusMsg, 64, "Reset (No ROM)");
      }
      cpu_reset(&cpu);
    }

    if (GuiButton((Rectangle){245, 5, 40, 20},
                  runEmulation ? "Pause" : "Run")) {
      runEmulation = !runEmulation;
    }

    if (GuiButton((Rectangle){290, 5, 40, 20}, "Step")) {
      runEmulation = false;
      cpu_step(&cpu);
    }

    // Disable main UI if dialog is open
    if (fileDialog.active)
      GuiLock();

    // --- CPU Status Panel ---
    GuiPanel((Rectangle){margin, topY, sidebarW, 200}, "CPU Registers");

    GuiLabel((Rectangle){margin + 15, topY + 30, 30, 20}, "PC:");
    if (!editPc)
      snprintf(regPcBuf, 5, "%04X", cpu.pc);
    if (GuiTextBox((Rectangle){margin + 45, topY + 30, 60, 20}, regPcBuf, 5,
                   editPc)) {
      editPc = !editPc;
      if (!editPc)
        cpu.pc = (uint16_t)strtol(regPcBuf, NULL, 16);
    }

    GuiLabel((Rectangle){margin + 15, topY + 55, 30, 20}, "A:");
    if (!editA)
      snprintf(regABuf, 3, "%02X", cpu.a);
    if (GuiTextBox((Rectangle){margin + 45, topY + 55, 40, 20}, regABuf, 3,
                   editA)) {
      editA = !editA;
      if (!editA)
        cpu.a = (uint8_t)strtol(regABuf, NULL, 16);
    }

    GuiLabel((Rectangle){margin + 15, topY + 80, 30, 20}, "X:");
    if (!editX)
      snprintf(regXBuf, 3, "%02X", cpu.x);
    if (GuiTextBox((Rectangle){margin + 45, topY + 80, 40, 20}, regXBuf, 3,
                   editX)) {
      editX = !editX;
      if (!editX)
        cpu.x = (uint8_t)strtol(regXBuf, NULL, 16);
    }

    GuiLabel((Rectangle){margin + 15, topY + 105, 30, 20}, "Y:");
    if (!editY)
      snprintf(regYBuf, 3, "%02X", cpu.y);
    if (GuiTextBox((Rectangle){margin + 45, topY + 105, 40, 20}, regYBuf, 3,
                   editY)) {
      editY = !editY;
      if (!editY)
        cpu.y = (uint8_t)strtol(regYBuf, NULL, 16);
    }

    GuiLabel((Rectangle){margin + 15, topY + 130, 30, 20}, "SP:");
    if (!editSp)
      snprintf(regSpBuf, 3, "%02X", cpu.sp);
    if (GuiTextBox((Rectangle){margin + 45, topY + 130, 40, 20}, regSpBuf, 3,
                   editSp)) {
      editSp = !editSp;
      if (!editSp)
        cpu.sp = (uint8_t)strtol(regSpBuf, NULL, 16);
    }

    // Flags visualization (NV-BDIZC)
    GuiLabel(
        (Rectangle){margin + 15, topY + 155, 180, 20},
        TextFormat(
            "Flags: %c%c-%c%c%c%c%c", (cpu.status & 0x80) ? 'N' : '.',
            (cpu.status & 0x40) ? 'V' : '.', (cpu.status & 0x10) ? 'B' : '.',
            (cpu.status & 0x08) ? 'D' : '.', (cpu.status & 0x04) ? 'I' : '.',
            (cpu.status & 0x02) ? 'Z' : '.', (cpu.status & 0x01) ? 'C' : '.'));

    GuiLabel((Rectangle){margin + 15, topY + 175, 180, 20},
             TextFormat("FPS: %d  Speed: %.2f MHz", GetFPS(),
                        (float)cyclesThisFrame * GetFPS() / 1000000.0f));

    GuiLabel((Rectangle){margin, topY + 205, 220, 20},
             "In:$00FF Snd:$E001 Vid:$2000");

    // --- Stack View (Bottom Left) ---
    Rectangle stackRect = {margin, scrH - margin - 120, sidebarW, 120};
    GuiPanel(stackRect, "Stack (Page 1)");
    for (int i = 0; i < 5; i++) {
      uint8_t offset = cpu.sp + i;
      int addr = 0x0100 + offset;
      uint8_t val = cpu.memory[addr];

      Color col = LIGHTGRAY;
      const char *prefix = "   ";
      if (i == 0) {
        col = RED; // Highlight SP
        prefix = "SP>";
      }
      DrawText(TextFormat("%s $%04X: %02X", prefix, addr, val),
               (int)stackRect.x + 10, (int)stackRect.y + 30 + i * 18, 10, col);
    }

    // --- Disassembly View ---
    float disasmY = topY + 230;
    float disasmH = stackRect.y - margin - disasmY;
    Rectangle disasmRect = {margin, disasmY, sidebarW, disasmH};
    GuiPanel(disasmRect, "Disassembly");

    uint16_t pc = cpu.pc;
    int maxDisasmLines = (int)((disasmRect.height - 30) / 20);
    for (int i = 0; i < maxDisasmLines; i++) {
      int y = (int)disasmRect.y + 30 + i * 20;

      const char *asmStr = Disassemble(&cpu, pc);

      // Breakpoint Toggle
      bool isBp = breakpoints[pc];
      if (GuiCheckBox((Rectangle){disasmRect.x + 5, (float)y, 15, 15}, "",
                      &isBp)) {
        breakpoints[pc] = isBp;
      }

      Color textColor = LIGHTGRAY;
      if (i == 0) {
        textColor = RED;
      }
      if (breakpoints[pc])
        textColor = BLUE;

      DrawText(TextFormat("$%04X: %s", pc, asmStr), (int)disasmRect.x + 25, y,
               10, textColor);
      pc += GetInstructionLength(cpu.memory[pc]);
    }

    // --- Memory Hex Editor ---
    Rectangle memRect = {rightX, topY, rightW, mainH};
    GuiPanel(memRect, showGraphics ? "Graphics Mode ($2000)" : "Memory View");

    if (GuiButton((Rectangle){memRect.x + memRect.width - 110, memRect.y + 5,
                              100, 20},
                  showGraphics ? "Show Hex" : "Show Screen")) {
      showGraphics = !showGraphics;
    }

    // Navigation Controls
    if (GuiButton((Rectangle){memRect.x + 10, memRect.y + 25, 30, 25}, "<"))
      memStart -= 0x100;
    if (GuiButton((Rectangle){memRect.x + 45, memRect.y + 25, 30, 25}, ">"))
      memStart += 0x100;

    GuiLabel((Rectangle){memRect.x + 90, memRect.y + 25, 40, 25}, "Addr:");
    if (GuiTextBox((Rectangle){memRect.x + 130, memRect.y + 25, 60, 25},
                   addrBuffer, 5, editAddrMode)) {
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
    int startY = (int)memRect.y + 100;
    int startX = (int)memRect.x + 10;

    if (showGraphics) {
      // Calculate scale to fit available space
      float availableWidth = memRect.width - 20;
      float availableHeight = memRect.height - 110; // 100 offset + 10 padding
      int scaleW = (int)(availableWidth / 32);
      int scaleH = (int)(availableHeight / 32);
      int scale = (scaleW < scaleH) ? scaleW : scaleH;
      if (scale < 1)
        scale = 1;

      int imgX = (int)(memRect.x +
                       (memRect.width - 32 * scale) / 2); // Center in panel

      for (int y = 0; y < 32; y++) {
        for (int x = 0; x < 32; x++) {
          uint8_t val = cpu.memory[0x2000 + y * 32 + x];
          Color col = PALETTE[val & 0x0F];
          DrawRectangle(imgX + x * scale, startY + y * scale, scale, scale,
                        col);
        }
      }
      DrawRectangleLines(imgX, startY, 32 * scale, 32 * scale, BLACK);
    } else {
      int maxRows = (int)((memRect.height - 100) / 20);
      for (int row = 0; row < maxRows; row++) {
        int rowAddr = memStart + row * 16;
        if (rowAddr >= MEM_SIZE)
          break;

        DrawText(TextFormat("0x%04X", rowAddr), startX, startY + row * 20, 10,
                 GRAY);

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
                   startY + row * 20, 10, WHITE);

          // ASCII
          char c = (val >= 32 && val <= 126) ? (char)val : '.';
          DrawText(TextFormat("%c", c), startX + 380 + col * 10,
                   startY + row * 20, 10, GRAY);
        }
      }
    }

    // Draw ROM Write Warning
    if (showRomWriteWarning) {
      DrawText("ROM WRITE ATTEMPT!", (int)(memRect.x + memRect.width / 2 - 100),
               (int)(memRect.y + memRect.height - 30), 20, RED);
    }

    // --- File Loader ---
    GuiLabel((Rectangle){memRect.x + 10, memRect.y + 60, 60, 25}, "Load Bin:");
    if (GuiTextBox((Rectangle){memRect.x + 70, memRect.y + 60, 150, 25},
                   fileBuffer, 64, editFileMode)) {
      editFileMode = !editFileMode;
    }

    if (GuiButton((Rectangle){memRect.x + 230, memRect.y + 60, 50, 25},
                  "Load")) {
      FILE *f = fopen(fileBuffer, "rb");
      if (f) {
        // Load at current memory view address (or fixed 0x0000/0x8000 depending
        // on preference) Here we load at memStart for flexibility
        fread(&cpu.memory[memStart], 1, MEM_SIZE - memStart, f);
        fclose(f);
        snprintf(statusMsg, 64, "Loaded at 0x%04X", memStart);
        runEmulation = true;
      } else {
        snprintf(statusMsg, 64, "Failed to open!");
        // Fallback: Fill video memory with noise to show graphics mode works
        for (int i = 0x2000; i < 0x2400; i++)
          cpu.memory[i] = GetRandomValue(0, 15);
      }
    }
    if (GuiButton((Rectangle){memRect.x + 285, memRect.y + 60, 25, 25},
                  "...")) {
      OpenFileDialog();
    }

    GuiLabel((Rectangle){memRect.x + 320, memRect.y + 60, 180, 25}, statusMsg);

    // --- Snapshots ---
    if (GuiButton((Rectangle){memRect.x + 410, memRect.y + 60, 60, 25},
                  "Save")) {
      SaveSnapshot(&cpu, "snapshot.sav");
      snprintf(statusMsg, 64, "Saved snapshot.sav");
    }
    if (GuiButton((Rectangle){memRect.x + 475, memRect.y + 60, 60, 25},
                  "Load")) {
      LoadSnapshot(&cpu, "snapshot.sav");
      snprintf(statusMsg, 64, "Loaded snapshot.sav");
    }

    // --- Bottom Panel (Console / Assembler) ---
    float tabY = topY + mainH + 5;
    Rectangle bottomRect = {rightX, tabY + 25, rightW, bottomH};

    // Tabs
    if (GuiButton((Rectangle){rightX, tabY, 80, 20}, "Console"))
      bottomTab = 0;
    if (GuiButton((Rectangle){rightX + 85, tabY, 80, 20}, "Assembler"))
      bottomTab = 1;
    if (GuiButton((Rectangle){rightX + 170, tabY, 80, 20}, "Profiler"))
      bottomTab = 2;

    if (bottomTab == 0) {
      GuiPanel(bottomRect, "Console Log ($E000)");
      GuiDrawText(consoleBuffer,
                  (Rectangle){bottomRect.x + 10, bottomRect.y + 20,
                              bottomRect.width - 20, bottomRect.height - 30},
                  TEXT_ALIGN_LEFT, LIGHTGRAY);
    } else if (bottomTab == 1) {
      GuiPanel(bottomRect, "Simple Assembler (Start: $0600)");
      if (GuiTextBoxMulti(
              (Rectangle){bottomRect.x + 10, bottomRect.y + 20,
                          bottomRect.width - 150, bottomRect.height - 30},
              asmSource, 1024, editAsm)) { // Use Multi-line text box
        editAsm = !editAsm;
      }
      if (GuiButton((Rectangle){bottomRect.x + bottomRect.width - 130,
                                bottomRect.y + 20, 120, 30},
                    "Compile")) {
        SimpleAssemble(&cpu, asmSource);
        snprintf(statusMsg, 64, "Assembled to $0600");
        cpu.pc = 0x0600; // Auto-jump to start
      }
    } else if (bottomTab == 2) {
      GuiPanel(bottomRect, "Profiler Stats");

      // Calculate stats
      uint64_t totalInstructions = 0;
      for (int i = 0; i < 256; i++) {
        totalInstructions += cpu.instruction_counts[i];
      }

      GuiLabel((Rectangle){bottomRect.x + 10, bottomRect.y + 20, 200, 20},
               TextFormat("Total Instr: %llu", totalInstructions));
      GuiLabel((Rectangle){bottomRect.x + 210, bottomRect.y + 20, 200, 20},
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

        DrawRectangle((int)bottomRect.x + 10, (int)bottomRect.y + 50 + i * 22,
                      (int)(percentage * 300), 18, BLUE);
        DrawText(TextFormat("$%02X: %llu (%.1f%%)", opcode, count,
                            percentage * 100.0f),
                 (int)bottomRect.x + 15, (int)bottomRect.y + 50 + i * 22 + 2,
                 10, WHITE);
      }
    }

    // --- File Dialog Overlay ---
    if (fileDialog.active) {
      GuiUnlock();
      DrawRectangle(0, 0, GetScreenWidth(), GetScreenHeight(),
                    Fade(BLACK, 0.5f));

      Rectangle winBounds = {(float)GetScreenWidth() / 2 - 200,
                             (float)GetScreenHeight() / 2 - 150, 400, 300};
      if (GuiWindowBox(winBounds, "Select File"))
        CloseFileDialog();

      // Up Button
      if (GuiButton((Rectangle){winBounds.x + 10, winBounds.y + 30, 30, 25},
                    "^")) {
        const char *parent = GetPrevDirectoryPath(fileDialog.dirPath);
        strncpy(fileDialog.dirPath, parent, 511);
        RefreshFileList();
      }
      GuiLabel((Rectangle){winBounds.x + 50, winBounds.y + 30, 340, 25},
               fileDialog.dirPath);

      // File List
      Rectangle listBounds = {winBounds.x + 10, winBounds.y + 60, 380, 200};
      GuiListViewEx(listBounds, (const char **)fileDialog.displayNames,
                    fileDialog.count, &fileDialog.scrollIndex,
                    &fileDialog.activeItem, &fileDialog.focusItem);

      // Buttons
      if (GuiButton((Rectangle){winBounds.x + 250, winBounds.y + 265, 60, 25},
                    "Open")) {
        if (fileDialog.activeItem >= 0 &&
            fileDialog.activeItem < fileDialog.count) {
          const char *selected = fileDialog.files.paths[fileDialog.activeItem];
          if (DirectoryExists(selected)) {
            strncpy(fileDialog.dirPath, selected, 511);
            RefreshFileList();
          } else {
            strncpy(fileBuffer, selected, 63);
            CloseFileDialog();
            // Auto-load
            FILE *f = fopen(fileBuffer, "rb");
            if (f) {
              fread(&cpu.memory[memStart], 1, MEM_SIZE - memStart, f);
              fclose(f);
              snprintf(statusMsg, 64, "Loaded: %s", GetFileName(fileBuffer));
              runEmulation = true;
            }
          }
        }
      }
      if (GuiButton((Rectangle){winBounds.x + 320, winBounds.y + 265, 60, 25},
                    "Cancel")) {
        CloseFileDialog();
      }
    }

    // --- Draw Pop-up Menus (Last for Z-order) ---
    if (menuFileActive) {
      Rectangle menuBounds = {5, 30, 120, 100};
      GuiUnlock(); // Ensure menu is clickable
      GuiPanel(menuBounds, NULL);
      if (GuiButton((Rectangle){menuBounds.x + 5, menuBounds.y + 5, 110, 25},
                    "Load ROM...")) {
        OpenFileDialog();
        menuFileActive = false;
      }
      if (GuiButton((Rectangle){menuBounds.x + 5, menuBounds.y + 35, 110, 25},
                    "Save State")) {
        SaveSnapshot(&cpu, "snapshot.sav");
        snprintf(statusMsg, 64, "Saved snapshot.sav");
        menuFileActive = false;
      }
      if (GuiButton((Rectangle){menuBounds.x + 5, menuBounds.y + 65, 110, 25},
                    "Exit")) {
        CloseWindow();
        return 0;
      }
      // Close if clicked outside
      if (IsMouseButtonPressed(MOUSE_LEFT_BUTTON) &&
          !CheckCollisionPointRec(GetMousePosition(), menuBounds) &&
          !CheckCollisionPointRec(GetMousePosition(),
                                  (Rectangle){5, 5, 60, 20})) {
        menuFileActive = false;
      }
    }

    if (menuEmulationActive) {
      Rectangle menuBounds = {70, 30, 120, 40};
      GuiUnlock();
      GuiPanel(menuBounds, NULL);
      // Add more emulation options here if needed
      if (IsMouseButtonPressed(MOUSE_LEFT_BUTTON) &&
          !CheckCollisionPointRec(GetMousePosition(), menuBounds) &&
          !CheckCollisionPointRec(GetMousePosition(),
                                  (Rectangle){70, 5, 80, 20})) {
        menuEmulationActive = false;
      }
    }

    if (menuHelpActive) {
      Rectangle menuBounds = {135, 30, 100, 40};
      GuiUnlock();
      GuiPanel(menuBounds, NULL);
      if (GuiButton((Rectangle){menuBounds.x + 5, menuBounds.y + 5, 90, 25},
                    "Manual")) {
        showManual = true;
        menuHelpActive = false;
      }
    }

    // --- Manual Window ---
    if (showManual) {
      GuiUnlock(); // Ensure we can interact with the manual
      DrawRectangle(0, 0, GetScreenWidth(), GetScreenHeight(),
                    Fade(BLACK, 0.5f));
      Rectangle manBounds = {(float)GetScreenWidth() / 2 - 200,
                             (float)GetScreenHeight() / 2 - 200, 400, 400};

      if (GuiWindowBox(manBounds, "6502 Manual"))
        showManual = false;

      Rectangle textBounds = {manBounds.x + 10, manBounds.y + 30,
                              manBounds.width - 20, manBounds.height - 40};

      // Use Read-Only TextBoxMulti for scrollable/selectable text
      GuiSetStyle(DEFAULT, TEXT_WRAP_MODE, TEXT_WRAP_WORD);
      GuiTextBoxMulti(textBounds, (char *)MANUAL_TEXT, 1024, false);
      GuiSetStyle(DEFAULT, TEXT_WRAP_MODE, TEXT_WRAP_NONE);
    }

    EndDrawing();
  }

  UnloadAudioStream(audioStream);
  CloseAudioDevice();
  CloseWindow();
  return 0;
}