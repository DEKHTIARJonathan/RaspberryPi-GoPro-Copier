# Raspberry PI GoPro Data Copier

This project aims to provide a quick solution to copy GoPro Video footages to a backup storage in places where bringing a computer is not convenient.

## Hardware

In order to build this project, you will need:

- 1x: Raspberry Pi Zero (v1 or v2 recommended)
- 1x: GPIO headers that you will need to solder on the Raspberry Pi Zero (if not already present)
- 1x: USB Hub Hat with passthrough headers
  - Waveshare USB Hat: https://www.waveshare.com/usb-hub-hat.htm
  - Waveshare USB + Ethernet Hat: https://www.waveshare.com/eth-usb-hub-hat.htm 
- 1x: 1.44in LCD Screen plus Joystick : https://www.waveshare.com/1.44inch-lcd-hat.htm
- [OPTIONAL] 1x: Battery module: https://www.waveshare.com/ups-hat-c.htm

## Assembly

Once you have all the components assembled together:

```bash
LCD Screen 
    |
    ﹀
  USB Hub
    |
    ﹀
 RPI Zero
    |
    ﹀
 Battery
```

 ## OS Install

 Please follow official raspberry pi tutorial and install Raspian (no GUI needed): https://www.raspberrypi.com/tutorials/how-to-set-up-raspberry-pi/

## Project install

### A. Enable Interfaces

* **Enable SPI Interface**

Necessary to enable the LCD screen to function.

More info on: https://www.waveshare.com/wiki/1.44inch_LCD_HAT

```bash
sudo raspi-config
Choose Interfacing Options -> SPI -> Yes to enable SPI interface
sudo reboot 0
```

* **[Optional] Enable I2C Interface**

If you intend to use the WaveShare Battery UPS Hat: https://www.waveshare.com/ups-hat-c.htm

It's recommend to enable the I2C Interface

```bash
sudo raspi-config 
Choose Interfacing Options -> I2C -> Yes to enable I2C interface
sudo reboot 0
```

### B. Clone the project

Please follow these steps:

```bash
sudo apt-get update
sudo apt-get install -y \
  wget curl vim git \
  python3.11 python3.11-dev \
  python3-pip
sudo rm /usr/lib/python3.11/EXTERNALLY-MANAGED  # Prevent PEP 668 annoyance
```

Then let's clone the project:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
cat ~/.ssh/id_ed25519.pub
```

```bash
cd ~/ 
git clone https://github.com/DEKHTIARJonathan/RaspberryPi-GoPro-Copier.git
cd RaspberryPi-GoPro-Copier
bash install_deps.sh
```

### C. Test & Verify Installation

* **Test the LCD Screen**

```bash
cd ~/RaspberryPi-GoPro-Copier

# Install Numpy
sudo apt update
sudo apt-get install -y libopenblas-dev  # Necessary for numpy
pip3 install --no-cache --upgrade numpy

python demo_LCD_screen.py   # CTRL + C to exit
```

* **[Optional] Test the UPS Batery Pack Screen**

You can test proper operation by doing:
```bash
cd ~/RaspberryPi-GoPro-Copier
python demo_UPS_hat.py
```

### D. Some configuration & setup

* **Configure USB AutoMount to automatically mount USB Storage devices**

Then we need to configure `usbmount`:

`sudo vi /etc/usbmount/usbmount.conf` to open the configuration file

And then:
```bash
# Replace: MOUNTOPTIONS="sync,noexec,nodev,noatime,nodiratime"   # Remove `sync` option
#      by: MOUNTOPTIONS="noexec,nodev,noatime,nodiratime"
#
# Replace: FILESYSTEMS="vfat ext2 ext3 ext4 hfsplus"
#      by: FILESYSTEMS="exfat ntfs fuseblk vfat ext2 ext3 ext4 hfsplus"
#
# Replace: FS_MOUNTOPTIONS=""
#      by: FS_MOUNTOPTIONS="-fstype=exfat,nls=utf8,uid=1000,gid=1000,umask=0002 -fstype=vfat,nls=utf8,uid=1000,gid=1000,umask=0002 -fstype=ntfs-3g,nls=utf8,uid=1000,gid=1000,umask=0002 -fstype=fuseblk,nls=utf8,uid=1000,gid=1000,umask=0002"
```

Then restart the service:

```bash
sudo systemctl daemon-reload
sudo service systemd-udevd --full-restart
```

* **Allow some sudo commands to require no passwords: reboot/shutdown/unmount**

Don't forget to replace `[your_username]` below

``` bash
$ sudo visudo
#     Add: %[your_username] ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot, /sbin/shutdown, /bin/umount
```

### E. Test the application manually

Launch the application as follows:

```bash
cd ~/RaspberryPi-GoPro-Copier
python gui.py
```

Once it is confirmed to work, you can close with `CTRL + C`

### E. Make the application to autostart at boot

* **Crontab to autostart our software**

Don't forget to replace `[your_username]` below

``` bash
$ sudo crontab -e  # Opens Crontab config file
#     Add: @reboot su [your_username] -c "/bin/bash /home/[your_username]/RaspberryPi-GoPro-Copier/startup.sh" >/home/[your_username]/RaspberryPi-GoPro-Copier/logs/cronlog 2>&1
```

* **Finally Reboot**
```bash
sudo reboot 0
```


