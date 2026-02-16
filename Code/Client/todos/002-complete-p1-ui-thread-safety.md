# P1: UI Thread Safety in recvmassage

## Issue
The `recvmassage` method runs in a Python Thread but directly calls `self.Ultrasonic.setText()` and `self.checkBox_Pinch_Object.setChecked()`. PyQt5 UI elements must only be modified from the main GUI thread.

## Location
- `Main.py` - recvmassage method

## Fix
Use pyqtSignal to emit data from the thread and connect to slots in mywindow. Create signals for ultrasonic updates and checkbox state.

## Priority
P1 - Can cause intermittent crashes
