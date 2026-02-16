# P2: Recording Thread Synchronization

## Issue
In `stop_listening`, the `_process_audio` thread starts immediately after setting `_recording = False`. The recording thread may still be doing a blocking read.

## Location
- `ai_mode.py` - `stop_listening` and `_record_audio` methods

## Fix
Use threading.Event to signal end of recording and join() the recording thread before starting processing.

## Priority
P2 - Could cause race on audio buffer
