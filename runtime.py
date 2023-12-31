#!/usr/bin/env python

import pyudev
import psutil

import hashlib
import os
import re
import shutil
import time

from collections import defaultdict 
from datetime import datetime
from functools import lru_cache 

from pathlib import Path
from pathlib import PosixPath

from copy_utils import DEFAULT_BUFFER_SIZE
from copy_utils import copy_with_callback


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


class VideoFile(PosixPath):

    @property
    def device_id(self):
        return str(self).split("/")[-4].replace("-", "_")
    
    @property
    @lru_cache
    def md5sum(self):
        md5_hash = hashlib.md5()
        with open(self,"rb") as f:
            # Read and update hash in chunks of 4K
            for byte_block in iter(lambda: f.read(4096),b""):
                md5_hash.update(byte_block)
            return md5_hash.hexdigest()

    @property
    @lru_cache
    def date_created(self):
        return VideoFile._date_to_str(
            VideoFile._timestamp_to_date(os.path.getctime(self))
        )
    
    @staticmethod
    def _date_to_str(date):
        return date.strftime("%Y_%m_%d")
    
    @property
    @lru_cache
    def date_last_modified(self):
        return VideoFile._date_to_str(
            VideoFile._timestamp_to_date(os.path.getmtime(self))
        )
    
    @staticmethod
    @lru_cache
    def _timestamp_to_date(tmstp):
        return datetime.fromtimestamp(tmstp).date()
    
    @property
    @lru_cache
    def size(self):
        return os.stat(self).st_size


class USBDevice(PosixPath):

    @property
    def device_id(self):
        return str(self).split("/")[-1].replace("-", "_")

    @lru_cache
    def is_gopro(self):
        return os.path.isfile(self / "Get_started_with_GoPro.url")

    @lru_cache
    def is_source(self):
        return self.is_gopro()
    
    @lru_cache
    def list_all_videos(self):
        dir_pattern = re.compile(r'^[0-9]{3}GOPRO$')
        video_dir = Path(self / "DCIM")

        video_dirs = list()
        for dir_name in _list_files_and_dirs(video_dir):
            obj_path = video_dir / dir_name
            if os.path.isdir(obj_path) and dir_pattern.match(dir_name):
                video_dirs.append(obj_path)
        
        videos = defaultdict(list) 
        for dir_name in video_dirs:
            for video_f in USBDevice.scan_dir_for_videos(dir_name):
                videos[video_f.date_created].append(video_f)

        for date in videos.keys():
            videos[date] = sorted(
                videos[date], 
                key=lambda v: v.date_created, 
                reverse=True
            )

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
                videos.append(VideoFile(filepath))

        return videos
    
    def umount(self):
        print(f"[INFO] Unmounting Device `{self}` ... ", end="", flush=True)
        if os.system(f'sudo umount {self}') == 0:
            print("SUCCESS !")
            return True
        
        else:
            print("ERROR !")
            return False
    

def get_usb_devices():
    context = pyudev.Context()

    removable_devices = [
        device 
        for device in context.list_devices(subsystem='block', DEVTYPE='disk') 
        if device.attributes.asstring('removable') == "1"
    ]

    device_list = list()
    for device in removable_devices:

        partitions = [
            device.device_node 
            for device in context.list_devices(subsystem='block', DEVTYPE='partition', parent=device)
        ]

        for p in psutil.disk_partitions():
            
            if p.device not in partitions:
                continue

            device_list.append(USBDevice(p.mountpoint))

    
    if len(device_list) > 2:
        raise RuntimeError(
            "Incorrect number of USB devices detected. "
            f"2 or less expected, received: {len(device_list)}")
    
    source_device = None
    target_device = None

    for device in device_list:
        if device.is_source():
            source_device = device
        else:
            target_device = device
    
    return source_device, target_device


def copy_file(source_f, target_device, dry_run=False):
    target_dir = Path(
        f"{target_device / source_f.date_created}____{source_f.device_id}"
    )

    try:
        os.makedirs(target_dir)
    except FileExistsError:
        pass

    target_f = VideoFile(target_dir / source_f.name)
    filesize_in_MB = round(source_f.size / (1<<17)) / 8 # bytes to MB

    print(f"[INFO] Copying: {source_f.name} => {target_f} - Size: {filesize_in_MB} MB ... ", flush=True)

    if not dry_run:
        try:
            start_t = time.perf_counter()
            from tqdm import tqdm
            bar_format = "{percentage:3.0f}% |{bar}| Elapsed: {elapsed} - Remaining:{remaining}"
            with tqdm(total=source_f.size, bar_format=bar_format) as bar:
                copy_with_callback(
                    source_f,
                    target_f,
                    follow_symlinks=True,
                    callback=lambda copied, total_copied, total: bar.update(copied),
                    buffer_size=DEFAULT_BUFFER_SIZE,
                )
            elapsed_t = round(time.perf_counter() - start_t)
            print(f"SUCCESS! Total: {elapsed_t:d} secs - Transfer: {float(filesize_in_MB)/elapsed_t:.1f} MB/s.")
        
        # If source and destination are same
        except shutil.SameFileError:
            print("SKIP: Same File")
        
        # If there is any permission issue
        except PermissionError:
            print("ERROR: Permission denied.")
        
        # For other errors
        except Exception as e:
            print(f"ERROR: {e}")


def get_or_create_target_dir(date, source_d, target_d):
    target_dir = Path(
        f"{target_d / date}____{source_d.device_id}"
    )

    try:
        os.makedirs(target_dir)
    except FileExistsError:
        pass

    return target_dir


if __name__ == "__main__":
    source_device, target_device = get_usb_devices()

    videos = source_device.list_all_videos()
    
    for id, video in enumerate(videos["2023_06_12"]):

        if id >= 5:
            break

        copy_file(video, target_device)