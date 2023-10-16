# -*- coding:utf-8 -*-
import LCD_1in44
import LCD_Config

import RPi.GPIO as GPIO

import copy
import math
import time
import os
import sys

from collections import defaultdict
from contextlib import contextmanager
from functools import lru_cache
from functools import partial
from pathlib import Path

from copy_utils import DEFAULT_BUFFER_SIZE
from copy_utils import copy_with_callback

from runtime import get_or_create_target_dir
from runtime import get_usb_devices
from runtime import USBPath
from runtime import VideoPath

from PIL import Image
from PIL import ImageDraw

__author__ = "Jonathan Dekhtiar"
__version__ = "1.0.0"


class VideoListing(object):
    def __init__(self, source_d: USBPath) -> None:
        self._videos_dict = source_d.list_all_videos()

    @property
    @lru_cache
    def days(self):
        return sorted(self._videos_dict.keys(), reverse=True)
    
    def get_videos(self, day):
        return self._videos_dict[day]


class Display(object):
    width = 128
    height = 128

    x_offset = 30
    y_offset = 14
    init_pos = (5, 5)

    max_height = height - (y_offset * 2)
    max_lines = 6

    def _setup_draw_disp_base(self):
        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        image = Image.new('RGB', (Display.width, Display.height))
        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)

        # Black background
        draw.rectangle((0, 0, Display.width, Display.height), outline=0, fill=0)

        return draw, image

    @contextmanager
    def get_draw_ctx(self):

        draw, image = self._setup_draw_disp_base()

        yield draw

        # Display
        self._disp.LCD_ShowImage(image,0,0)

    @property
    def source_d(self):
        if self._source_d is None:
            raise RuntimeError("`source_d` is not defined ...")
        
        return self._source_d

    @source_d.setter
    def source_d(self, device):
        if self._source_d is not None:
            raise RuntimeError("`source_d` is already defined ...")
        
        if not isinstance(device, USBPath):
            raise ValueError(f"`source_d` should be an instance of `USBPath`, received: {type(device)}")
        
        self._source_d = device

    @property
    def target_d(self):
        if self._target_d is None:
            raise RuntimeError("`target_d` is not defined ...")
        
        return self._target_d

    @target_d.setter
    def target_d(self, device):
        if self._target_d is not None:
            raise RuntimeError("`target_d` is already defined ...")
        
        if not isinstance(device, USBPath):
            raise ValueError(f"`target_d` should be an instance of `USBPath`, received: {type(device)}")
        
        self._target_d = device

    @property
    def days(self):        
        return self.videos.days

    @property
    def videos(self):
        if self._videos is None:
            self._videos = VideoListing(source_d=self.source_d)
        
        return self._videos

    @property
    @lru_cache
    def line_struct(self):
        y_pos = copy.copy(Display.init_pos[1])

        struct = list()
        for _ in range(Display.max_lines):
            y_pos += Display.y_offset
            struct.append(copy.copy(y_pos))

        return struct
    
    @property
    @lru_cache
    def num_pages(self):
        return math.ceil(len(self.days) / Display.max_lines)

    def __init__(self) -> None:
        self._videos = None
        self._source_d = None
        self._target_d = None

        # 240x240 display with hardware SPI:
        self._disp = LCD_1in44.LCD()
        Lcd_ScanDir = LCD_1in44.SCAN_DIR_DFT  #SCAN_DIR_DFT = D2U_L2R
        self._disp.LCD_Init(Lcd_ScanDir)
        self._disp.LCD_Clear()

        self._page_idx = 0
        self._cur_pos = 0

        self.disp_welcome_screen()
    
    def disp_welcome_screen(self):

        with self.get_draw_ctx() as draw:
            
            line_len = 21
            draw.text((10, 15), "GO PRO DATA COPIER", fill="WHITE")
            draw.text((0, 35), "-" * line_len, fill="WHITE")
            draw.text((12, 53), f"{__author__}", fill="WHITE")
            draw.text((22, 68), f"Version: {__version__}", fill="WHITE")
            draw.text((0, 85), "-" * line_len, fill="WHITE")
            draw.text((18, 105), f"... LOADING ...", fill="WHITE")

        time.sleep(5)  # Force display of the welcome screen for 5 secs.

    def disp_refresh_day_selector(self):

        with self.get_draw_ctx() as draw:

            # Base Layout
            draw.text(Display.init_pos, "Days Available:", fill="WHITE")
            draw.text((Display.width - 30, Display.height - Display.y_offset), "EXIT", fill="WHITE")
        
            days = self.days[self._page_idx * Display.max_lines:]
            for idx, day in enumerate(days):
                if idx >= Display.max_lines:
                    break

                y_pos = self.line_struct[idx]
                draw.text((Display.x_offset, y_pos), day, fill="WHITE")

            if len(days) > Display.max_lines:
                draw.text((Display.x_offset + 23, y_pos + Display.y_offset), "...", fill="WHITE")

            # Print cursor
            if self._cur_pos >= Display.max_lines:
                raise ValueError(f"Invalid `cur_pos` received: {self._cur_pos=}. Should be < {Display.max_lines}")
            
            if self._cur_pos >= 0:
                draw.text((Display.x_offset - 10, self.line_struct[self._cur_pos]), ">", fill="WHITE")

            else:
                draw.text((Display.width - 40, Display.height - Display.y_offset), ">", fill="WHITE")

    def move_up(self):
        self._cur_pos -= 1

        # Verify we don't exceed top position
        if self._cur_pos < 0:
            self._page_idx -= 1
            self._cur_pos = Display.max_lines - 1

            # Verify we don't exceed top page
            if self._page_idx < 0:
                # we revert to same as before
                self._cur_pos = self._page_idx = 0

        self.disp_refresh_day_selector()

    def move_down(self):
        old_cur = self._cur_pos
        self._cur_pos += 1

        # Verify we don't exceed max_lines
        if self._cur_pos >= Display.max_lines:
            self._page_idx += 1
            self._cur_pos = 0

            # Verify we don't exceed num_pages
            if self._page_idx >= self.num_pages:
                # we revert to same as before
                self._page_idx -= 1
                self._cur_pos = old_cur

        # We verify the cursor doesn't exceed the number of line in the last page
        day_idx = Display.max_lines * self._page_idx + (self._cur_pos + 1)
        if day_idx > len(self.days):
            # we revert to same as before
            self._cur_pos = old_cur

        self.disp_refresh_day_selector()

    def move_to_exit(self):
        self._cur_pos = -1
        self.disp_refresh_day_selector()
    
    def move_to_days(self):
        self._cur_pos = 0
        self.disp_refresh_day_selector()

    def press_select(self):
        if self._cur_pos == -1:
            print("[INFO] Unmounting USB Devices ...")
            assert(self.source_d.umount())
            assert(self.target_d.umount())
            print("[INFO] Cleaning up GPIO")
            GPIO.cleanup()
            print("[INFO] Now shutting down ...")
            time.sleep(2)
            os.system('sudo shutdown now')
            sys.exit(0)

        else:
            selected_day = self.days[self._page_idx * Display.max_lines:][self._cur_pos]
            self.disp_copy_screen_loop(date=selected_day)
            self.disp_refresh_day_selector()  # return to date select screen

    def exec_loop(self):

        self.disp_wait_for_USB_devices_ready_loop()
        
        KEY_UP_PIN     = 6 
        KEY_DOWN_PIN   = 19
        KEY_LEFT_PIN   = 5
        KEY_RIGHT_PIN  = 26
        KEY_PRESS_PIN  = 13
        KEY1_PIN       = 21
        KEY2_PIN       = 20
        KEY3_PIN       = 16

        #init GPIO
        GPIO.setmode(GPIO.BCM) 

        GPIO.setup(KEY_UP_PIN,      GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        GPIO.setup(KEY_DOWN_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        GPIO.setup(KEY_LEFT_PIN,    GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        GPIO.setup(KEY_RIGHT_PIN,   GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        GPIO.setup(KEY_PRESS_PIN,   GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        GPIO.setup(KEY1_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        GPIO.setup(KEY2_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up
        GPIO.setup(KEY3_PIN,        GPIO.IN, pull_up_down=GPIO.PUD_UP)      # Input with pull-up

        # print the initial selector screen
        self.disp_refresh_day_selector()

        try:
            while True:
                # UP Arrow is pressed
                Display.test_key_press(KEY_UP_PIN, callback_fn=display.move_up)

                # DOWN Arrow is pressed
                Display.test_key_press(KEY_DOWN_PIN, callback_fn=display.move_down)

                # LEFT Arrow is pressed
                Display.test_key_press(KEY_LEFT_PIN, callback_fn=display.move_to_days)

                # RIGHT Arrow is pressed
                Display.test_key_press(KEY_RIGHT_PIN, callback_fn=display.move_to_exit)
                
                # CENTER BTN is pressed
                Display.test_key_press(KEY_PRESS_PIN, callback_fn=display.press_select)

                time.sleep(0.1)
        except Exception as e:
            GPIO.cleanup()
            raise

        except KeyboardInterrupt:
            GPIO.cleanup()

    @staticmethod
    def test_key_press(key, callback_fn):
        if GPIO.input(key) == 0:  # CENTER is pressed
            callback_fn()
            # wait for release
            while GPIO.input(key) == 0:
                time.sleep(0.1)

    @staticmethod
    def _draw_progress_bar(draw, pos_x, pos_y, bar_width, height, progress, fg=(211,211,211)):
        current_width = int(bar_width * progress)

        draw.rectangle((pos_x, pos_y, pos_x + current_width, pos_y + height), fill=fg)

    def disp_copy_screen_loop(self, date):

        videos = self.videos.get_videos(day=date)

        target_dir = get_or_create_target_dir(
            date=date, 
            source_d=self.source_d, 
            target_d=self.target_d
        )

        for idx, source_f in enumerate(videos):

            target_f = VideoPath(target_dir / source_f.name)

            filesize_in_MB = round(source_f.size / (1<<17)) / 8  # bytes to MB

            print(f"[LOG] Copying: {source_f.name} => {target_f} - Size: {filesize_in_MB} MB ... ", flush=True)

            draw, image = self._setup_draw_disp_base()
                
            line_len = 21
            # Base Layout
            draw.text((21, 15), f"~ {date} ~", fill="WHITE")
            draw.text((0, 35), "-" * line_len, fill="WHITE")

            # General Progress Data
            draw.text((5, 53), f"COPY: {idx + 1:04d}/{len(videos):04d} ...", fill="WHITE")

            draw.text((5, 68), f"Size: {filesize_in_MB:.1f} MB", fill="WHITE")
            draw.text((0, 85), "-" * line_len, fill="WHITE")

            # Verifying the file doesn't already exist in the target device
            if target_f.is_file():

                # Writing Hash Verification Msg
                draw.text((15, 105), "Checking Hash ...", fill="WHITE")
                self._disp.LCD_ShowImage(image,0,0)
                
                # Pre-emptively mask message with a black bar displayed at next `LCD_ShowImage`
                draw.rectangle((0, 90, Display.width, Display.height), fill="BLACK")
                if target_f.size == source_f.size and target_f.md5sum and source_f.md5sum:
                    print(f"[LOG] File `{source_f}` already exists => Skipped.")
                    continue
                else:  # Files are different - Delete and Overwrite
                    target_f.unlink()

            # Progress bar Update Fn
            bar_x_offset = 10
            def bar_callback_fn(copied, total_copied, total):
                Display._draw_progress_bar(
                    draw=draw,
                    pos_x=bar_x_offset,
                    pos_y=105,
                    bar_width=Display.width - (bar_x_offset * 2), 
                    height=10,
                    progress=total_copied /total  #  Between 0..1
                )
                self._disp.LCD_ShowImage(image,0,0)
            
            # for progress in range(0, 100, 3):
            #     update_fn(None, progress, 100)
            copy_with_callback(
                source_f,
                target_f,
                follow_symlinks=True,
                callback=bar_callback_fn,
                buffer_size=DEFAULT_BUFFER_SIZE,
            )

    def disp_wait_for_USB_devices_ready_loop(self):

        while True:
            source_d, target_d = get_usb_devices()

            if source_d is not None and target_d is not None:
                break

            with self.get_draw_ctx() as draw:
                draw.text((10, 25), "Waiting for USB:", fill="WHITE")
                draw.text((10, 55), f"* Source: {source_d if source_d is None else source_d.device_id}", fill="WHITE")
                draw.text((10, 85), f"* Target: {target_d if target_d is None else target_d.device_id}", fill="WHITE")

            time.sleep(1)

        self.source_d = source_d
        self.target_d = target_d

if __name__ == "__main__":

    display = Display()

    display.exec_loop()
