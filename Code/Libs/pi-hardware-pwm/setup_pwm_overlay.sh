#!/bin/bash

model=$(cat /proc/cpuinfo | grep 'Model' | uniq | awk -F: '{print $2}' | xargs)

if [[ "$model" == *"Raspberry Pi 5"* ]]; then
  # Step 1: Compile the DTS file to DTB
  dtc -I dts -O dtb -o pwm-pi5.dtbo pwm-pi5-overlay.dts

  # Check if the compilation was successful
  if [ $? -ne 0 ]; then
    echo "Error compiling DTS file. Exiting."
    exit 1
  fi

  # Step 2: Copy the DTB file to the overlays directory
  sudo cp pwm-pi5.dtbo /boot/firmware/overlays/

  # Check if the copy was successful
  if [ $? -ne 0 ]; then
    echo "Error copying DTB file. Exiting."
    exit 1
  fi

  # Step 3: Check if 'dtoverlay=pwm-pi5' is already in config.txt
  config_file="/boot/firmware/config.txt"
  if ! grep -q "dtoverlay=pwm-pi5" "$config_file"; then
    # If not found, append 'dtoverlay=pwm-pi5' to the end of config.txt
    echo "dtoverlay=pwm-pi5" | sudo tee -a "$config_file"
    
    # Check if the append was successful
    if [ $? -ne 0 ]; then
      echo "Error appending to config.txt. Exiting."
      exit 1
    fi
  else
    echo "'dtoverlay=pwm-pi5' already exists in config.txt. Skipping append."
  fi

  echo "Setup completed successfully."
else
  config_file="/boot/firmware/config.txt"
  overlay_line="dtoverlay=pwm-2chan,pin=12,func=4,pin2=13,func2=4"
 
  if ! grep -q "$overlay_line" "$config_file"; then
    echo "$overlay_line" | sudo tee -a "$config_file"
    if [ $? -ne 0 ]; then
      echo "Error appending to config.txt. Exiting."
      exit 1
    fi
    echo "Added '$overlay_line' to /boot/firmware/config.txt."
  else
    echo "'$overlay_line' already exists in /boot/firmware/config.txt. Skipping append."
  fi
fi
 
echo "Script execution completed."