# P2: TTS Response Validation

## Issue
`_speak_with_gemini` accesses `tts_response.candidates[0].content.parts[0].inline_data.data` directly. If API returns safety block or empty candidates, raises IndexError.

## Location
- `ai_mode.py` - `_speak_with_gemini` method

## Fix
Add validation before accessing nested response structure. Handle empty/blocked responses gracefully.

## Priority
P2 - Will crash on safety-filtered responses
