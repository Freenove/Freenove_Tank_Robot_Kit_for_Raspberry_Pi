# P2: PyAudio Resource Safety

## Issue
`AIModeSession.stop()` calls `self._pyaudio.terminate()` which can crash if streams are still active.

## Location
- `ai_mode.py` - `stop()` method and `_record_audio`, `_speak_with_gemini`

## Fix
1. Track active streams
2. Stop and close all streams before terminate()
3. Use finally blocks for stream cleanup

## Priority
P2 - Can cause segfault on exit
