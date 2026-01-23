#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Writes a 2-byte little-endian integer
void write_u16(FILE *f, uint16_t v) {
  fputc(v & 0xFF, f);
  fputc((v >> 8) & 0xFF, f);
}

// Writes a 4-byte little-endian integer
void write_u32(FILE *f, uint32_t v) {
  fputc(v & 0xFF, f);
  fputc((v >> 8) & 0xFF, f);
  fputc((v >> 16) & 0xFF, f);
  fputc((v >> 24) & 0xFF, f);
}

int main() {
  const int width = 32;
  const int height = 32;
  const int bpp = 32;

  FILE *f = fopen("icon.ico", "wb");
  if (!f) {
    perror("Error opening icon.ico for writing");
    return 1;
  }

  // --- ICONDIR ---
  write_u16(f, 0); // Reserved
  write_u16(f, 1); // Type (1=Icon)
  write_u16(f, 1); // Count

  // --- ICONDIRENTRY ---
  fputc(width, f);
  fputc(height, f);
  fputc(0, f);       // Palette size
  fputc(0, f);       // Reserved
  write_u16(f, 1);   // Planes
  write_u16(f, bpp); // BPP

  int pixel_data_size = width * height * 4;
  int mask_data_size = (width * height) / 8;
  int header_size = 40;
  int total_size = header_size + pixel_data_size + mask_data_size;

  write_u32(f, total_size); // Size
  write_u32(f, 22);         // Offset (6 + 16)

  // --- BITMAPINFOHEADER ---
  write_u32(f, header_size);
  write_u32(f, width);
  write_u32(f, height * 2); // Height * 2 for mask
  write_u16(f, 1);          // Planes
  write_u16(f, bpp);
  write_u32(f, 0); // Compression
  write_u32(f, pixel_data_size + mask_data_size);
  write_u32(f, 0);
  write_u32(f, 0);
  write_u32(f, 0);
  write_u32(f, 0);

  // --- Pixel Data (BGRA, Bottom-Up) ---
  uint8_t canvas[32][32][4]; // [y][x][BGRA]
  memset(canvas, 0, sizeof(canvas));

  // Draw Chip Body (Black/Dark Grey)
  // Centered, width 16 (8..23), height 28 (2..29)
  for (int y = 2; y < 30; y++) {
    for (int x = 8; x < 24; x++) {
      canvas[y][x][0] = 40;  // B
      canvas[y][x][1] = 40;  // G
      canvas[y][x][2] = 40;  // R
      canvas[y][x][3] = 255; // Alpha
    }
  }

  // Draw Pins (Silver)
  // 10 pins per side
  for (int i = 0; i < 10; i++) {
    int py = 3 + i * 3; // y positions: 3, 6, 9...
    if (py + 1 >= 30)
      break;

    // Left Pins
    for (int px = 4; px < 8; px++) {
      for (int dy = 0; dy < 2; dy++) {
        canvas[py + dy][px][0] = 180;
        canvas[py + dy][px][1] = 180;
        canvas[py + dy][px][2] = 180;
        canvas[py + dy][px][3] = 255;
      }
    }
    // Right Pins
    for (int px = 24; px < 28; px++) {
      for (int dy = 0; dy < 2; dy++) {
        canvas[py + dy][px][0] = 180;
        canvas[py + dy][px][1] = 180;
        canvas[py + dy][px][2] = 180;
        canvas[py + dy][px][3] = 255;
      }
    }
  }

  // Draw Notch (Top center)
  // y=28 is near top (since 0 is bottom)
  for (int y = 28; y < 30; y++) {
    for (int x = 14; x < 18; x++) {
      canvas[y][x][0] = 20; // Darker
      canvas[y][x][1] = 20;
      canvas[y][x][2] = 20;
    }
  }

  // Write pixels
  for (int y = 0; y < 32; y++) {
    for (int x = 0; x < 32; x++) {
      fwrite(canvas[y][x], 1, 4, f);
    }
  }

  // --- Mask Data (1 bit per pixel) ---
  // 0 = Opaque, 1 = Transparent
  // 32 pixels wide = 4 bytes per row.
  for (int y = 0; y < 32; y++) {
    for (int x = 0; x < 32; x += 8) {
      uint8_t mask_byte = 0;
      for (int b = 0; b < 8; b++) {
        // If alpha is 0, it's transparent (1)
        if (canvas[y][x + b][3] == 0) {
          mask_byte |= (1 << (7 - b));
        }
      }
      fputc(mask_byte, f);
    }
  }

  fclose(f);
  return 0;
}
