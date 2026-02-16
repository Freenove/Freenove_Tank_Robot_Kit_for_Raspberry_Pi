#!/bin/bash
# =============================================================================
# Freenove Tank Robot - Mac Client Setup
# Run this on your Mac to set up the control client
# =============================================================================

cd ~/Documents/GitHub/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code

echo "=============================================="
echo "Setting up Mac Client for Freenove Tank Robot"
echo "=============================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Install from python.org or brew install python3"
    exit 1
fi

echo ""
echo "Installing Mac dependencies..."
python3 setup_macos.py

echo ""
echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo ""
echo "To run the client:"
echo "  cd ~/Documents/GitHub/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Client"
echo "  python3 Main.py"
echo ""
echo "Then enter your Pi's IP address and click Connect."
echo ""
