# -*- coding:utf-8 -*-
import LCD_1in44
import LCD_Config

import RPi.GPIO as GPIO

import copy
import math
import time
import sys

from contextlib import contextmanager
from functools import lru_cache

from PIL import Image
from PIL import ImageDraw

__author__ = "Jonathan Dekhtiar"
__version__ = "0.0.1"


class Display(object):
    width = 128
    height = 128

    x_offset = 30
    y_offset = 14
    init_pos = (5, 5)

    max_height = height - (y_offset * 2)
    max_lines = 6

    @contextmanager
    def get_draw_ctx(self):
        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        image = Image.new('RGB', (Display.width, Display.height))
        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)

        # Black background
        draw.rectangle((0, 0, Display.width, Display.height), outline=0, fill=0)

        yield draw

        # Display
        self._disp.LCD_ShowImage(image,0,0)

    @property
    def days(self):
        if self._days is None:
            raise RuntimeError("Days are not defined ...")
        
        return self._days

    @days.setter
    def days(self, day_list):
        if self._days is not None:
            raise RuntimeError("Days is already defined ...")
        
        if not isinstance(day_list, list):
            raise ValueError(f"`day_list` should be a list, received: {type(day_list)}")
        
        self._days = copy.deepcopy(day_list)

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
        self._days = None

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
            GPIO.cleanup()
            sys.exit(0)

        else:
            selected_day = self.days[self._page_idx * Display.max_lines:][self._cur_pos]
            self.progress_screen(date=selected_day)
            self.disp_refresh_day_selector()  # return to date select screen

    def exec_loop(self, days):
        self.days = days
        
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
    def _draw_progress_bar(draw, pos_x, pos_y, width, height, progress, fg=(211,211,211)):
        width = int(width * progress)
        diameter = int(min(height, width))

        draw.rectangle((pos_x + (diameter / 2), pos_y, pos_x + width - (diameter / 2), pos_y + height), fill=fg, width=10)
        # Start Ellipse
        draw.ellipse((pos_x, pos_y, pos_x + diameter, pos_y + height), fill=fg)
        # End Ellipse
        if width > diameter:
            draw.ellipse((pos_x + width - diameter, pos_y, pos_x + width, pos_y + height), fill=fg)

    def progress_screen(self, date):
        num_files = 5

        for idx in range(1, num_files + 1):

            # size = 536870912 >> 20  # bytes to megabytes
            import random
            file_size = random.randint(100, 4000)
            
            for progress in range(33):

                progress *= 3

                with self.get_draw_ctx() as draw:
                    
                    line_len = 21
                    # Base Layout
                    draw.text((21, 15), f"~ {date} ~", fill="WHITE")
                    draw.text((0, 35), "-" * line_len, fill="WHITE")

                    # Progress Data
                    draw.text((5, 53), f"COPY: {idx:04d}/{num_files:04d} ...", fill="WHITE")

                    draw.text((5, 68), f"Size: {file_size} MB", fill="WHITE")
                    draw.text((0, 85), "-" * line_len, fill="WHITE")

                    bar_x_offset = 10

                    Display._draw_progress_bar(
                        draw=draw,
                        pos_x=bar_x_offset,
                        pos_y=105,
                        width=Display.width - (bar_x_offset * 2), 
                        height=10,
                        progress=progress / 100.  #  Between 0..1
                    )


if __name__ == "__main__":

    display = Display()

    days = [
        "2023_10_02",
        "2023_02_02",
        "2023_04_02",
        "2023_11_02",
        "2023_10_07",
        "2023_02_01",
        "2023_12_02",
        "2023_04_07",
        "2023_01_22",
        "2023_01_07"
    ]

    days = sorted(days, reverse=True)

    time.sleep(5)
    display.exec_loop(days=days)
