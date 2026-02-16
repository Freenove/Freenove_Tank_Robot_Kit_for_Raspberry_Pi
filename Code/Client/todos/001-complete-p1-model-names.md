# P1: Invalid Model Names

## Issue
The code uses `gemini-2.5-flash-preview`, `gemini-2.5-flash-preview-tts`, and `gemini-3-flash-preview` which may not exist in production.

## Location
- `ai_mode.py:63` - TTS_MODEL
- `ai_mode.py:267` - Agent model
- `ai_mode.py:479` - STT model

## Fix
Verify model names against current Gemini API. The models ARE valid preview models (gemini-3-flash-preview is the latest). Add fallback handling if model not found.

## Priority
P1 - Could cause 404 errors if models unavailable
