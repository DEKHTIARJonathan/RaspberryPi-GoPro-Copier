#!/usr/bin/env python
import pyudev
import psutil

import os
import re
import shutil
import time

from datetime import datetime
from functools import lru_cache 


from pathlib import Path
from pathlib import PosixPath


# USB AutoMount:
# $ sudo apt install usbmount
# $ sudo vi /etc/usbmount/usbmount.conf
#     Add: `FILESYSTEMS="exfat vfat ext2 ext3 ext4 hfsplus"`
#     Add: `FS_MOUNTOPTIONS="-fstype=vfat,uid=1000,gid=1000,dmask=0077,fmask=0177"`
# $ sudo reboot 0

# Add to crontab:
# $ sudo crontab -e
#     Add: @reboot python /path/to/file.py >/home/jonathan/logs/cronlog 2>&1

# Install Dependencies
# pip install -u pyudev psutil

def _list_files_and_dirs(dir_path):
    res = []
    try:
        for file_path in os.listdir(dir_path):
            fullpath = os.path.join(dir_path, file_path)
            if os.path.isfile(fullpath) or os.path.isdir(fullpath):
                res.append(file_path)
    except FileNotFoundError:
        print(f"The directory {dir_path} does not exist")
    except PermissionError:
        print(f"Permission denied to access the directory {dir_path}")
    except OSError as e:
        print(f"An OS error occurred: {e}")
    return res


class VideoPath(PosixPath):

    @property
    @lru_cache
    def date_created(self):
        return VideoPath._date_to_str(
            VideoPath._timestamp_to_date(os.path.getctime(self))
        )
    
    @staticmethod
    def _date_to_str(date):
        return date.strftime("%Y_%m_%d")
    
    @property
    @lru_cache
    def date_last_modified(self):
        return VideoPath._date_to_str(
            VideoPath._timestamp_to_date(os.path.getmtime(self))
        )
    
    @staticmethod
    @lru_cache
    def _timestamp_to_date(tmstp):
        return datetime.fromtimestamp(tmstp).date()


class USBPath(PosixPath):
    @lru_cache
    def is_gopro(self):
        return os.path.isfile(self / "Get_started_with_GoPro.url")
    
    @lru_cache
    def list_all_videos(self):
        dir_pattern = re.compile(r'^[0-9]{3}GOPRO$')
        video_dir = Path(self / "DCIM")

        video_dirs = list()
        for dir_name in _list_files_and_dirs(video_dir):
            obj_path = video_dir / dir_name
            if os.path.isdir(obj_path) and dir_pattern.match(dir_name):
                video_dirs.append(obj_path)
        
        videos = list()
        for dir_name in video_dirs:
            for video_f in USBPath.scan_dir_for_videos(dir_name):
                videos.append(video_f)

        return videos
    
    @staticmethod
    @lru_cache
    def scan_dir_for_videos(dir):
        videos = list()

        for filename in _list_files_and_dirs(dir):
            filepath = dir / filename

            if not os.path.isfile(filepath):
                continue

            if str(filepath).lower().endswith(".mp4"):
                videos.append(VideoPath(filepath))

        return sorted(videos, key=lambda v: v.date_created, reverse=True)
    


def get_usb_devices():
    context = pyudev.Context()

    removable = [
        device 
        for device in context.list_devices(subsystem='block', DEVTYPE='disk') 
        if device.attributes.asstring('removable') == "1"
    ]

    device_list = list()
    for device in removable:

        partitions = [
            device.device_node 
            for device in context.list_devices(subsystem='block', DEVTYPE='partition', parent=device)
        ]

        for p in psutil.disk_partitions():
            
            if p.device not in partitions:
                continue

            device_list.append(USBPath(p.mountpoint))

    
    if len(device_list) != 2:
        raise RuntimeError(
            "Incorrect number of USB devices detected. "
            f"2 expected, received: {len(device_list)}")
    
    go_pro_device = None
    target_device = None

    for device in device_list:
        if device.is_gopro():
            go_pro_device = device
        else:
            target_device = device

    if go_pro_device is None or target_device is None:
        raise RuntimeError(
            "Incorrect device detected:"
            f"\n\t- [0] {device[0]} => Is Go Pro: {device[0].is_gopro()}"
            f"\n\t- [1] {device[1]} => Is Go Pro: {device[1].is_gopro()}"
        )
    
    return go_pro_device, target_device


def copy_file(source, target_device):
    target_dir = target_device / source.date_created

    try:
        os.makedirs(target_dir)
        print("created")
    except FileExistsError:
        print("exists")
        pass

    target = target_dir / source.name
    print(f"{source=}")
    print(f"{target=}")
    try:
        print("Starting Copy ...")
        start_t = time.perf_counter()
        shutil.copy(source, target)
        elapsed_t = round(time.perf_counter() - start_t)
        print(f"File `{source}` copied successfully - {elapsed_t:d} secs.")
    
    # If source and destination are same
    except shutil.SameFileError:
        print("Source and destination represents the same file.")
    
    # If there is any permission issue
    except PermissionError:
        print("Permission denied.")
    
    # For other errors
    except Exception as e:
        print(f"Error occurred while copying file: {e}.")

if __name__ == "__main__":
    gopro_device, target_device = get_usb_devices()

    videos = gopro_device.list_all_videos()
    print(f"{videos=}")
    # video_dates = list(set([vid.date_created for vid in videos]))
    # print(f"{video_dates=}")
    for video in videos:
        copy_file(video, target_device)