#!/bin/bash

model=$(cat /proc/cpuinfo | grep 'model name' | uniq | awk -F: '{print $2}' | xargs)

if [[ "$model" == *"Raspberry Pi 5"* ]]; then
    local_file="./pwm-pi5.dtbo"
    overlays_file="/boot/firmware/overlays/pwm-pi5.dtbo"
    config_file="/boot/firmware/config.txt"

    if [ -f "$local_file" ]; then
        rm "$local_file"
    fi

    if [ -f "$overlays_file" ]; then
        sudo rm "$overlays_file"
    fi

    if grep -q "dtoverlay=pwm-pi5" "$config_file"; then
        sudo sed -i '/dtoverlay=pwm-pi5/d' "$config_file"
    fi
else
    config_file="/boot/firmware/config.txt"
    overlay_line="dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4"

    if grep -q "$overlay_line" "$config_file"; then
        sudo sed -i "/$overlay_line/d" "$config_file"
        echo "Removed '$overlay_line' from config.txt."
    else
        echo "'$overlay_line' not found in config.txt. Nothing to remove."
    fi
fi

echo "All operations completed."