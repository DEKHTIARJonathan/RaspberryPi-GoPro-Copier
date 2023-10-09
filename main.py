#!/usr/bin/env python
import pyudev
import psutil

import os
import glob

context = pyudev.Context()

removable = [device for device in context.list_devices(subsystem='block', DEVTYPE='disk') if device.attributes.asstring('removable') == "1"]
for device in removable:
    partitions = [device.device_node for device in context.list_devices(subsystem='block', DEVTYPE='partition', parent=device)]
    print("All removable partitions: {}".format(", ".join(partitions)))
    print("Mounted removable partitions:")
    for p in psutil.disk_partitions():
        if p.device in partitions:
            print("Drive Found: {} => {}".format(p.device, p.mountpoint))
            video_path = os.path.join(p.mountpoint, "/**/*.MP4")
            for file in glob.iglob(f"{video_path}/", recursive=True):
                print(f"\t- {file}")
            print(os.listdir(p.mountpoint))
        if os.path.isfile(os.path.join(p.mountpoint, "Get_started_with_GoPro.url")):
            print("GO PRO SD Card Found !")