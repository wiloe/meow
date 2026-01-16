#ifndef MEOWGUI_H
#define MEOWGUI_H

#include "raygui.h"
#include <ctype.h>

// Helper to check for keywords
static bool IsAsmKeyword(const char *word) {
  static const char *keywords[] = {
      "LDA", "LDX", "LDY", "STA", "STX", "STY", "TAX", "TAY",  "TXA",  "TYA",
      "TSX", "TXS", "PHA", "PHP", "PLA", "PLP", "AND", "EOR",  "ORA",  "BIT",
      "ADC", "SBC", "CMP", "CPX", "CPY", "INC", "DEC", "INX",  "DEX",  "INY",
      "DEY", "ASL", "LSR", "ROL", "ROR", "JMP", "JSR", "RTS",  "BCC",  "BCS",
      "BEQ", "BMI", "BNE", "BPL", "BVC", "BVS", "CLC", "CLD",  "CLI",  "CLV",
      "SEC", "SED", "SEI", "BRK", "NOP", "RTI", "ORG", "BYTE", "WORD", NULL};
  char upper[16];
  int i = 0;
  while (word[i] && i < 15) {
    upper[i] = toupper(word[i]);
    i++;
  }
  upper[i] = 0;
  for (int k = 0; keywords[k]; k++) {
    if (strcmp(upper, keywords[k]) == 0)
      return true;
  }
  return false;
}

// Text Box control with multiple lines
int GuiTextBoxMulti(Rectangle bounds, char *text, int textSize, bool editMode) {
#if !defined(RAYGUI_TEXTBOX_AUTO_CURSOR_COOLDOWN)
#define RAYGUI_TEXTBOX_AUTO_CURSOR_COOLDOWN                                    \
  20 // Frames to wait for autocursor movement
#endif
#if !defined(RAYGUI_TEXTBOX_AUTO_CURSOR_DELAY)
#define RAYGUI_TEXTBOX_AUTO_CURSOR_DELAY                                       \
  1 // Frames delay for autocursor movement
#endif

  int result = 0;
  GuiState state = GuiGetState();

  int wrapMode = GuiGetStyle(DEFAULT, TEXT_WRAP_MODE);

  // NOTE: GetTextBounds is static in raygui.h, we replicate logic or assume
  // bounds are correct Since we can't call static functions from another file
  // easily without including the implementation, and we are in a header
  // included by main.c, we rely on main.c having RAYGUI_IMPLEMENTATION.
  // However, static functions are internal to the translation unit.
  // We will reimplement GetTextBounds logic here for safety.
  Rectangle textBounds = bounds;
  textBounds.x = bounds.x + GuiGetStyle(TEXTBOX, BORDER_WIDTH);
  textBounds.y = bounds.y + GuiGetStyle(TEXTBOX, BORDER_WIDTH) +
                 GuiGetStyle(TEXTBOX, TEXT_PADDING);
  textBounds.width = bounds.width - 2 * GuiGetStyle(TEXTBOX, BORDER_WIDTH) -
                     2 * GuiGetStyle(TEXTBOX, TEXT_PADDING);
  textBounds.height = bounds.height - 2 * GuiGetStyle(TEXTBOX, BORDER_WIDTH) -
                      2 * GuiGetStyle(TEXTBOX, TEXT_PADDING);
  if (GuiGetStyle(TEXTBOX, TEXT_ALIGNMENT) == TEXT_ALIGN_RIGHT)
    textBounds.x -= GuiGetStyle(TEXTBOX, TEXT_PADDING);
  else
    textBounds.x += GuiGetStyle(TEXTBOX, TEXT_PADDING);

  int textLength =
      (text != NULL) ? (int)strlen(text) : 0; // Get current text length

  // We need access to textBoxCursorIndex. It is static in raygui.h.
  // If this file is included in main.c after raygui.h, it can access it if it
  // wasn't static. Since it IS static, we cannot access it directly. We will
  // use a local static variable for this control or try to hack it. For now,
  // let's use a local static, which means cursor position won't be shared with
  // other textboxes correctly (resetting one won't reset this one), but it's a
  // compromise for a separate file. BETTER: We can't easily share the internal
  // cursor index. We will manage our own.
  static int localCursorIndex = 0;
  static bool ctrlToggle = false;
  int thisCursorIndex = localCursorIndex;

  if (thisCursorIndex > textLength)
    thisCursorIndex = textLength;
  int textIndexOffset = 0; // Text index offset to start drawing in the box

  // Cursor rectangle
  Rectangle cursor = {0};

  // Multiline cursor positioning logic
  int cursorLine = 0;
  int cursorLineStart = 0;
  for (int i = 0; i < thisCursorIndex; i++) {
    if (text[i] == '\n') {
      cursorLine++;
      cursorLineStart = i + 1;
    }
  }
  int textWidthInLine = GuiGetTextWidth(text + cursorLineStart) -
                        GuiGetTextWidth(text + thisCursorIndex);
  cursor.x =
      textBounds.x + textWidthInLine + GuiGetStyle(DEFAULT, TEXT_SPACING);
  cursor.y =
      textBounds.y + cursorLine * (GuiGetStyle(DEFAULT, TEXT_SIZE) +
                                   GuiGetStyle(DEFAULT, TEXT_LINE_SPACING));
  cursor.width = 2;
  cursor.height = (float)GuiGetStyle(DEFAULT, TEXT_SIZE);

  if (cursor.height >= bounds.height)
    cursor.height = bounds.height - GuiGetStyle(TEXTBOX, BORDER_WIDTH) * 2;
  if (cursor.y < (bounds.y + GuiGetStyle(TEXTBOX, BORDER_WIDTH)))
    cursor.y = bounds.y + GuiGetStyle(TEXTBOX, BORDER_WIDTH);

  // Update control
  if ((state != STATE_DISABLED) &&            // Control not disabled
      !GuiGetStyle(TEXTBOX, TEXT_READONLY) && // TextBox not on read-only mode
      !GuiIsLocked() &&                       // Gui not locked
      (wrapMode == TEXT_WRAP_NONE))           // No wrap mode
  {
    Vector2 mousePosition = GetMousePosition();

    if (editMode) {
      static int autoCursorCounter = 0;
      if (IsKeyPressed(KEY_LEFT_CONTROL) || IsKeyPressed(KEY_RIGHT_CONTROL)) {
        ctrlToggle = !ctrlToggle;
      }
      if (IsKeyDown(KEY_LEFT) || IsKeyDown(KEY_RIGHT) || IsKeyDown(KEY_UP) ||
          IsKeyDown(KEY_DOWN) || IsKeyDown(KEY_BACKSPACE) ||
          IsKeyDown(KEY_DELETE))
        autoCursorCounter++;
      else
        autoCursorCounter = 0;

      bool autoCursorShouldTrigger =
          (autoCursorCounter > RAYGUI_TEXTBOX_AUTO_CURSOR_COOLDOWN) &&
          ((autoCursorCounter % RAYGUI_TEXTBOX_AUTO_CURSOR_DELAY) == 0);

      state = STATE_PRESSED;

      if (localCursorIndex > textLength)
        localCursorIndex = textLength;

      int codepoint = GetCharPressed(); // Get Unicode codepoint
      if (IsKeyPressed(KEY_ENTER))
        codepoint = (int)'\n';

      // Encode codepoint as UTF-8
      int codepointSize = 0;
      const char *charEncoded = CodepointToUTF8(codepoint, &codepointSize);

      // Handle text paste action
      if (IsKeyPressed(KEY_V) && (ctrlToggle)) {
        const char *pasteText = GetClipboardText();
        if (pasteText != NULL) {
          int pasteLength = 0;
          int pasteCodepoint;
          int pasteCodepointSize;

          while (true) {
            pasteCodepoint =
                GetCodepointNext(pasteText + pasteLength, &pasteCodepointSize);
            if (textLength + pasteLength + pasteCodepointSize >= textSize)
              break;
            pasteLength += pasteCodepointSize;
          }

          if (pasteLength > 0) {
            for (int i = textLength; i >= localCursorIndex; i--)
              text[i + pasteLength] = text[i];

            for (int i = 0; i < pasteLength; i++)
              text[localCursorIndex + i] = pasteText[i];

            localCursorIndex += pasteLength;
            textLength += pasteLength;
            text[textLength] = '\0';
          }
        }
      } else if (((codepoint == (int)'\n') || (codepoint >= 32)) &&
                 ((textLength + codepointSize) < textSize)) {
        for (int i = (textLength + codepointSize); i > localCursorIndex; i--)
          text[i] = text[i - codepointSize];

        for (int i = 0; i < codepointSize; i++)
          text[localCursorIndex + i] = charEncoded[i];

        localCursorIndex += codepointSize;
        textLength += codepointSize;
        text[textLength] = '\0';
      }

      if ((textLength > 0) && IsKeyPressed(KEY_HOME))
        localCursorIndex = 0;

      if ((textLength > localCursorIndex) && IsKeyPressed(KEY_END))
        localCursorIndex = textLength;

      if ((textLength > localCursorIndex) && IsKeyPressed(KEY_DELETE) &&
          (ctrlToggle)) {
        // Ctrl+Delete logic omitted for brevity, falling back to simple delete
        int nextCodepointSize = 0;
        GetCodepointNext(text + localCursorIndex, &nextCodepointSize);
        for (int i = localCursorIndex + nextCodepointSize; i <= textLength; i++)
          text[i - nextCodepointSize] = text[i];
        textLength -= nextCodepointSize;
      } else if ((textLength > localCursorIndex) &&
                 (IsKeyPressed(KEY_DELETE) ||
                  (IsKeyDown(KEY_DELETE) && autoCursorShouldTrigger))) {
        int nextCodepointSize = 0;
        GetCodepointNext(text + localCursorIndex, &nextCodepointSize);
        for (int i = localCursorIndex + nextCodepointSize; i <= textLength; i++)
          text[i - nextCodepointSize] = text[i];
        textLength -= nextCodepointSize;
      }

      if ((localCursorIndex > 0) && IsKeyPressed(KEY_BACKSPACE) &&
          (ctrlToggle)) {
        // Ctrl+Backspace logic omitted for brevity
        int prevCodepointSize = 0;
        GetCodepointPrevious(text + localCursorIndex, &prevCodepointSize);
        for (int i = localCursorIndex; i <= textLength; i++)
          text[i - prevCodepointSize] = text[i];
        textLength -= prevCodepointSize;
        localCursorIndex -= prevCodepointSize;
      } else if ((localCursorIndex > 0) &&
                 (IsKeyPressed(KEY_BACKSPACE) ||
                  (IsKeyDown(KEY_BACKSPACE) && autoCursorShouldTrigger))) {
        int prevCodepointSize = 0;
        GetCodepointPrevious(text + localCursorIndex, &prevCodepointSize);
        for (int i = localCursorIndex; i <= textLength; i++)
          text[i - prevCodepointSize] = text[i];
        textLength -= prevCodepointSize;
        localCursorIndex -= prevCodepointSize;
      }

      if ((localCursorIndex > 0) &&
          (IsKeyPressed(KEY_LEFT) ||
           (IsKeyDown(KEY_LEFT) && autoCursorShouldTrigger))) {
        int prevCodepointSize = 0;
        GetCodepointPrevious(text + localCursorIndex, &prevCodepointSize);
        localCursorIndex -= prevCodepointSize;
      } else if ((textLength > localCursorIndex) &&
                 (IsKeyPressed(KEY_RIGHT) ||
                  (IsKeyDown(KEY_RIGHT) && autoCursorShouldTrigger))) {
        int nextCodepointSize = 0;
        GetCodepointNext(text + localCursorIndex, &nextCodepointSize);
        localCursorIndex += nextCodepointSize;
      }

      // Move cursor position with mouse
      if (CheckCollisionPointRec(mousePosition, textBounds)) {
        // Mouse click logic simplified: find closest char
        // This is complex to replicate perfectly without access to internal
        // font data easily For now, we trust the user clicks somewhere and we
        // might not update cursor perfectly on mouse click in this standalone
        // function without duplicating all logic. We will skip mouse cursor
        // placement for this helper to keep it simple and compilable.
        if (IsMouseButtonPressed(MOUSE_LEFT_BUTTON)) {
          // Placeholder: move to end if clicked
          // localCursorIndex = textLength;
        }
      }

      // Re-calculate cursor line/pos for drawing
      cursorLine = 0;
      cursorLineStart = 0;
      for (int i = 0; i < localCursorIndex; i++)
        if (text[i] == '\n') {
          cursorLine++;
          cursorLineStart = i + 1;
        }
      cursor.x = textBounds.x +
                 (GuiGetTextWidth(text + cursorLineStart) -
                  GuiGetTextWidth(text + localCursorIndex)) +
                 GuiGetStyle(DEFAULT, TEXT_SPACING);
      cursor.y =
          textBounds.y + cursorLine * (GuiGetStyle(DEFAULT, TEXT_SIZE) +
                                       GuiGetStyle(DEFAULT, TEXT_LINE_SPACING));

      if (!CheckCollisionPointRec(mousePosition, bounds) &&
          IsMouseButtonPressed(MOUSE_LEFT_BUTTON)) {
        localCursorIndex = 0;
        autoCursorCounter = 0;
        result = 1;
      }
    } else {
      if (CheckCollisionPointRec(mousePosition, bounds)) {
        state = STATE_FOCUSED;
        if (IsMouseButtonPressed(MOUSE_LEFT_BUTTON)) {
          localCursorIndex = textLength;
          result = 1;
        }
      }
    }
  }

  // Draw control
  // We need to draw the rectangle manually since we can't call static
  // GuiDrawRectangle We use standard Raylib DrawRectangle functions
  Color borderColor = GetColor(GuiGetStyle(TEXTBOX, BORDER + (state * 3)));
  Color baseColor = BLANK;
  if (state == STATE_PRESSED)
    baseColor = GetColor(GuiGetStyle(TEXTBOX, BASE_COLOR_PRESSED));
  else if (state == STATE_DISABLED)
    baseColor = GetColor(GuiGetStyle(TEXTBOX, BASE_COLOR_DISABLED));

  int borderWidth = GuiGetStyle(TEXTBOX, BORDER_WIDTH);

  // Draw Base
  if (baseColor.a > 0)
    DrawRectangle((int)bounds.x, (int)bounds.y, (int)bounds.width,
                  (int)bounds.height, baseColor);

  // Draw Border
  if (borderWidth > 0) {
    DrawRectangle((int)bounds.x, (int)bounds.y, (int)bounds.width, borderWidth,
                  borderColor);
    DrawRectangle((int)bounds.x, (int)bounds.y + borderWidth, borderWidth,
                  (int)bounds.height - 2 * borderWidth, borderColor);
    DrawRectangle((int)bounds.x + (int)bounds.width - borderWidth,
                  (int)bounds.y + borderWidth, borderWidth,
                  (int)bounds.height - 2 * borderWidth, borderColor);
    DrawRectangle((int)bounds.x,
                  (int)bounds.y + (int)bounds.height - borderWidth,
                  (int)bounds.width, borderWidth, borderColor);
  }

  // Draw text
  // We use a custom draw loop to handle newlines which GuiDrawText might not
  // handle exactly as we want for editing But GuiDrawText is static. We must
  // use DrawTextEx from Raylib.
  Font font = GuiGetFont();
  Color textColor = GetColor(GuiGetStyle(TEXTBOX, TEXT + (state * 3)));

  // We need to draw line by line
  float yOffset = 0;

  // Simple line drawing
  int start = 0;
  for (int i = 0; i <= textLength; i++) {
    if (text[i] == '\n' || text[i] == '\0') {
      char lineBuffer[1024];
      int len = i - start;
      if (len > 1023)
        len = 1023;
      strncpy(lineBuffer, text + start, len);
      lineBuffer[len] = '\0';

      // Syntax Highlighting Drawing
      float currentX = textBounds.x;
      int k = 0;
      while (lineBuffer[k]) {
        int chunkLen = 0;
        Color col = textColor;

        if (lineBuffer[k] == ';') {
          // Comment
          chunkLen = strlen(lineBuffer + k);
          col = GRAY;
        } else if (isdigit(lineBuffer[k]) || lineBuffer[k] == '$' ||
                   lineBuffer[k] == '#') {
          // Number/Immediate
          col = VIOLET;
          chunkLen = 1;
          while (lineBuffer[k + chunkLen] &&
                 !isspace(lineBuffer[k + chunkLen]) &&
                 lineBuffer[k + chunkLen] != ';')
            chunkLen++;
        } else if (isalpha(lineBuffer[k]) || lineBuffer[k] == '.') {
          // Word
          while (lineBuffer[k + chunkLen] &&
                 (isalnum(lineBuffer[k + chunkLen]) ||
                  lineBuffer[k + chunkLen] == '_' ||
                  lineBuffer[k + chunkLen] == '.'))
            chunkLen++;
          char word[64];
          if (chunkLen < 64) {
            strncpy(word, lineBuffer + k, chunkLen);
            word[chunkLen] = 0;
            if (IsAsmKeyword(word))
              col = GOLD;
            else if (lineBuffer[k + chunkLen] == ':') {
              col = RED;
              chunkLen++;
            } // Label definition
          }
        } else {
          // Other chars (punctuation, space)
          chunkLen = 1;
        }

        char chunk[1024];
        if (chunkLen > 1023)
          chunkLen = 1023;
        strncpy(chunk, lineBuffer + k, chunkLen);
        chunk[chunkLen] = 0;

        DrawTextEx(font, chunk, (Vector2){currentX, textBounds.y + yOffset},
                   (float)GuiGetStyle(DEFAULT, TEXT_SIZE),
                   (float)GuiGetStyle(DEFAULT, TEXT_SPACING), col);

        Vector2 size =
            MeasureTextEx(font, chunk, (float)GuiGetStyle(DEFAULT, TEXT_SIZE),
                          (float)GuiGetStyle(DEFAULT, TEXT_SPACING));
        currentX += size.x;
        k += chunkLen;
      }

      yOffset += GuiGetStyle(DEFAULT, TEXT_SIZE) +
                 GuiGetStyle(DEFAULT, TEXT_LINE_SPACING);
      start = i + 1;
    }
  }

  // Draw cursor
  if (editMode && !GuiGetStyle(TEXTBOX, TEXT_READONLY)) {
    DrawRectangleRec(cursor,
                     GetColor(GuiGetStyle(TEXTBOX, BORDER_COLOR_PRESSED)));
  }

  return result;
}

#endif // MEOWGUI_H