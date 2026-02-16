#!/bin/bash
# =============================================================================
# Freenove Tank Robot - Quick Test Runner
# Run individual component tests interactively
# =============================================================================
# Usage: bash PI_TEST_ALL.sh
# =============================================================================

cd ~/Freenove_Tank_Robot_Kit_for_Raspberry_Pi/Code/Server

# Ensure pigpiod is running (required for V1.0 PCB)
echo "Starting pigpiod daemon..."
sudo killall pigpiod 2>/dev/null || true
sudo pigpiod
sleep 1

echo ""
echo "=============================================="
echo "Freenove Tank Robot - Test Menu"
echo "=============================================="
echo ""
echo "IMPORTANT: Turn ON both S1 and S2 switches on PCB!"
echo ""
echo "Select a test to run:"
echo "  1) LED test       - Color patterns cycle"
echo "  2) Motor test     - Forward/back/left/right"
echo "  3) Servo test     - Arm opens/closes"
echo "  4) Ultrasonic     - Distance readings (HC-SR04)"
echo "  5) Infrared       - Line sensor readings"
echo "  6) Camera test    - Saves image.jpg"
echo "  7) Lidar test     - Distance readings (TF-Mini S)"
echo "  8) Sonic mode     - Obstacle avoidance (standalone)"
echo "  9) Line tracking  - Follow line (standalone)"
echo " 10) Start server   - Full server with gamepad"
echo "  0) Exit"
echo ""

read -p "Enter choice [0-10]: " choice

case $choice in
    1)
        echo "Running LED test... (Ctrl+C to stop)"
        sudo python test.py Led
        ;;
    2)
        echo "Running Motor test... (Ctrl+C to stop)"
        sudo python test.py Motor
        ;;
    3)
        echo "Running Servo test... (Ctrl+C to stop)"
        sudo python test.py Servo
        ;;
    4)
        echo "Running Ultrasonic test... (Ctrl+C to stop)"
        sudo python test.py Ultrasonic
        ;;
    5)
        echo "Running Infrared test... (Ctrl+C to stop)"
        sudo python test.py Infrared
        ;;
    6)
        echo "Running Camera test (5 seconds)..."
        sudo python test.py camera
        echo "Image saved to image.jpg"
        ;;
    7)
        echo "Running Lidar test... (Ctrl+C to stop)"
        echo "NOTE: Requires TF-Mini S sensor connected via USB-UART"
        sudo python test.py Lidar
        ;;
    8)
        echo "Running Sonic obstacle avoidance... (Ctrl+C to stop)"
        sudo python car.py Sonic
        ;;
    9)
        echo "Running Line tracking mode... (Ctrl+C to stop)"
        sudo python car.py Infrared
        ;;
    10)
        echo "Starting server with gamepad support..."
        echo "Plug in USB dongle BEFORE pressing Enter!"
        read -p "Press Enter to start..."
        sudo python main.py
        ;;
    0)
        echo "Exiting."
        ;;
    *)
        echo "Invalid choice."
        ;;
esac
