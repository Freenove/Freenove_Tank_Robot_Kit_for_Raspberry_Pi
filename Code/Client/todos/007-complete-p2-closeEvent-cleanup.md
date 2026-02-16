# P2: Missing Cleanup in closeEvent

## Issue
When window is closed, `stop_ai_mode()` is never called. Audio devices and sockets may remain open.

## Location
- `Main.py` - `closeEvent` method (or lack thereof)

## Fix
Override closeEvent to call stop_ai_mode() before closing.

## Priority
P2 - Resource leak on exit
