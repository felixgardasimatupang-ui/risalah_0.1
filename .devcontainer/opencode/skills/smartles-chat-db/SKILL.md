---
name: smartles-chat-db
description: Full-cycle development loop for SmartLes Chat-DB — Telegram Bot + Gemini AI + Google Sheets. Run server, debug Gemini API errors, fix data sync, improve display, tune AI prompts.
license: MIT
compatibility: opencode
metadata:
  stack: python, fastapi, telegram-bot, gemini-ai, google-sheets
  project: smartles-chat-db
---

## What I do

Handle every aspect of the SmartLes Chat-DB project in a tight loop: run server → catch errors → fix → repeat until stable. I cover the full stack from bot logic to AI prompt tuning to Sheets operations.

## Project facts

- **Location**: `/Users/felix/Documents/Project Sementara/otomasi`
- **Run command**: `./run.sh` or `uvicorn src.main:app --reload --host 0.0.0.0 --port 8080`
- **Python**: 3.11+, dependencies via `.venv/`
- **AI**: Google Gemini (`gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-1.5-flash` fallback chain)
- **Database**: Google Sheets via `gspread`
- **Config**: `.env` file — `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `GOOGLE_SHEET_ID`, `GOOGLE_SHEETS_CREDENTIALS_PATH`
- **Mock AI mode**: Set `USE_MOCK_AI=true` in `.env` to bypass Gemini for testing
- **Config class**: `src/config.py` → `Settings` with env mapping

## Source map

| Layer | File | Purpose |
|-------|------|---------|
| Entry | `src/main.py` | FastAPI app, startup/shutdown, webhook vs polling |
| Bot | `src/bot/telegram.py` | Message handler, confirmation flow, history |
| Bot | `src/bot/router.py` | FastAPI webhook endpoint |
| AI | `src/ai/processor.py` | Gemini integration, function calling, fallback chain |
| AI | `src/ai/tools.py` | Tool definitions (11 functions) + executors |
| AI | `src/ai/mock_processor.py` | Mock mode for offline testing |
| Sheets | `src/sheets/client.py` | `gspread` client + sheet access |
| Sheets | `src/sheets/operations.py` | CRUD operations + green highlight |
| Sheets | `src/sheets/color.py` | Cell color formatting |
| Utils | `src/utils/display.py` | Format amount, format table |
| Utils | `src/utils/formatter.py` | Error formatting |
| Utils | `src/utils/sanitizer.py` | Phone sanitization |
| Utils | `src/utils/image.py` | Render data as image |
| Utils | `src/utils/evaluator.py` | Summaries for siswa/koperasi/tabungan |
| Test | `tests/` | pytest with pytest-asyncio |

## Common issues & fixes

### 1. Gemini API 400 error: "Role 'assistant' is not supported"
**Cause**: Conversation history uses `role: "assistant"` but Gemini requires `role: "model"`.
**Fix**: Check `src/ai/processor.py` — ensure all history entries use `"role": "model"` not `"role": "assistant"`.

### 2. Gemini quota exhausted (429)
**Cause**: Free tier rate limits.
**Fix**: Already handled via `_call_with_fallback` which tries 3 models. If all fail, falls back to mock processor.

### 3. Data not showing / sync issues
**Check**:
- Google Sheet ID is correct in `.env`
- Credentials JSON is valid and sheet is shared with the service account email
- Sheet tab names match `SHEET_NAME_*` config
- `gspread` can access the sheet — run `python3 -c "from src.sheets.client import get_sheet; s=get_sheet(); print(s.title)"`

### 4. Mock AI not working
**Set** `USE_MOCK_AI=true` in `.env` and restart. The mock processor in `src/ai/mock_processor.py` handles basic patterns.

### 5. Bot not responding
**Check**:
- Bot token is correct
- Server is running (check terminal for `Application started` log)
- If polling: ensure no other instance is running
- If webhook: ensure URL is publicly accessible and `HOST` is not `0.0.0.0`

### 6. Display / formatting issues
**Files**: `src/utils/display.py`, `src/utils/formatter.py`, `src/utils/image.py`
**Image rendering**: `render_text_as_image()` in `src/utils/image.py` — fallback if text display is ugly

## Workflow

1. **Run server**: `./run.sh` or full `uvicorn` command
2. **On error**: Read the stack trace, identify source file, fix, save (auto-reload)
3. **Verify**: Send test message via Telegram
4. **If mock mode**: Set `USE_MOCK_AI=true` for faster dev cycle
5. **On data issues**: Inspect Google Sheet directly, check config, restart
6. **Loop**: Repeat until all issues resolved
