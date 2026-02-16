# P2: Race Condition in Brain Initialization

## Issue
`_ensure_brain_async` initializes global objects without a lock. Concurrent calls could trigger multiple initializations.

## Location
- `ai_mode.py` - `_ensure_brain_async` function

## Fix
Add asyncio.Lock to wrap the initialization check.

## Priority
P2 - Unlikely in push-to-talk but should be fixed
