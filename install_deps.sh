#!/bin/bash

sudo apt-get update

# 1. Install exfat & NTFS support
sudo apt-get install -y exfat-fuse exfat-utils ntfs-3g

# 2. Install usbmount to allow USB devices auto mount.
sudo apt-get install -y usbmount

# 3. Install Pillow Dependencies
sudo apt-get install -y libopenjp2-7

# 4. Install Pillow Dependencies
pip3 install --no-cache --upgrade -r requirements.txt
