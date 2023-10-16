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

#### A. Clone the project

Please follow these steps:

```bash
sudo apt-get update
sudo apt-get install -y wget curl vim git
```

Then let's clone the project:

```bash
cd ~/ 
git clone https://github.com/DEKHTIARJonathan/RaspberryPi-GoPro-Copier.git
cd RaspberryPi-GoPro-Copier
```

#### B. Install Dependencies for the LCD Screen

Many of these steps are detailled here: https://www.waveshare.com/wiki/1.44inch_LCD_HAT

* **Install BCM2835 libraries**

```bash
wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.71.tar.gz
tar zxvf bcm2835-1.71.tar.gz
cd bcm2835-1.71/
sudo ./configure && sudo make && sudo make check && sudo make install
# For more information, please refer to the official website: http://www.airspayce.com/mikem/bcm2835/
```

* **Install wiringPi libraries**

```bash
sudo apt-get update
sudo apt-get install wiringpi
#For Raspberry Pi systems after May 2019 (earlier than before, you may not need to execute), you may need to upgrade:
wget https://project-downloads.drogon.net/wiringpi-latest.deb
sudo dpkg -i wiringpi-latest.deb
gpio -v
# Run gpio -v and version 2.52 will appear. If it does not appear, the installation is wrong
```

* **Install Python libraries**

```bash
sudo apt-get update
sudo apt-get install python3-pip
sudo apt-get install python3-pil
sudo apt-get install python3-numpy
sudo pip3 install RPi.GPIO
sudo pip3 install spidev
```

* **Test the Program**

```bash
cd python
python main.py
python key_demo.py
```

* **Reboot**

```bash
sudo reboot 0
```

#### C. Install Python Dependencies for the program

```bash
cd ~/RaspberryPi-GoPro-Copier
pip install -r requirements.txt
```

#### D. Some configuration & setup

* **Install ExFat Support**

```bash
# Install exFat support (always useful)
sudo apt-get update
sudo apt-get install exfat-fuse exfat-utils
```

* **Install USB AutoMount to automatically mount USB Storage devices**

```bash
sudo apt-get update
sudo apt install usbmount
```

Then we need to configure `usbmount`:

`sudo vi /etc/usbmount/usbmount.conf` to open the configuration file

And then:
```bash
# Replace: MOUNTOPTIONS="sync,noexec,nodev,noatime,nodiratime"   # Remove `sync` option
#      by: MOUNTOPTIONS="noexec,nodev,noatime,nodiratime"

#     Add: `FILESYSTEMS="exfat vfat ext2 ext3 ext4 hfsplus"`
#     Add: `FS_MOUNTOPTIONS="-fstype=exfat,uid=1000,gid=1000,umask=0002 -fstype=vfat,uid=1000,gid=1000,umask=0002"`
```

* **Crontab to autostart our software**

Don't forget to replace `[your_username]` below

``` bash
$ sudo crontab -e  # Opens Crontab config file
#     Add: @reboot su [your_username] -c "/bin/bash /home/[your_username]/RaspberryPi-GoPro-Copier/startup.sh" >/home/[your_username]/RaspberryPi-GoPro-Copier/logs/cronlog 2>&1
```

* **Allow some sudo commands to require no passwords: reboot/shutdown/unmount**

``` bash
$ sudo visudo
#     Add: %[your_username] ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot, /sbin/shutdown, /bin/umount
```

* **Finally Reboot**
```bash
sudo reboot 0
```


