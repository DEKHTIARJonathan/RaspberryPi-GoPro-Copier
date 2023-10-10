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

        # Base Layout
        draw.text(Display.init_pos, "Days Available:", fill = "WHITE")
        draw.text((Display.width - 30, Display.height - Display.y_offset), "EXIT", fill="WHITE")

        yield draw

        # Display
        self._disp.LCD_ShowImage(image,0,0)

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
        return math.ceil(len(self._days) / Display.max_lines)

    def __init__(self, days) -> None:
        self._days = days

        # 240x240 display with hardware SPI:
        self._disp = LCD_1in44.LCD()
        Lcd_ScanDir = LCD_1in44.SCAN_DIR_DFT  #SCAN_DIR_DFT = D2U_L2R
        self._disp.LCD_Init(Lcd_ScanDir)
        self._disp.LCD_Clear()

        self._page_idx = 0
        self._cur_pos = 0

        with self.get_draw_ctx() as draw:
            self.refresh_display(draw=draw)
    
    def refresh_display(self, draw):
        
        days = self._days[self._page_idx * Display.max_lines:]
        for idx, day in enumerate(days):
            if idx >= Display.max_lines:
                break

            y_pos = self.line_struct[idx]
            draw.text((Display.x_offset, y_pos), day, fill = "WHITE")

        if len(days) > Display.max_lines:
            draw.text((Display.x_offset + 23, y_pos + Display.y_offset), "...", fill = "WHITE")

        # Print cursor
        if self._cur_pos >= Display.max_lines:
            raise ValueError(f"Invalid `cur_pos` received: {self._cur_pos=}. Should be < {Display.max_lines}")
        
        if self._cur_pos >= 0:
            draw.text((Display.x_offset - 10, self.line_struct[self._cur_pos]), ">", fill = "WHITE")

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

        with self.get_draw_ctx() as draw:
            self.refresh_display(draw=draw)

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
        if day_idx > len(self._days):
            # we revert to same as before
            self._cur_pos = old_cur

        with self.get_draw_ctx() as draw:
            self.refresh_display(draw=draw)

    def move_to_exit(self):
        self._cur_pos = -1
        with self.get_draw_ctx() as draw:
            self.refresh_display(draw=draw)
    
    def move_to_days(self):
        self._cur_pos = 0
        with self.get_draw_ctx() as draw:
            self.refresh_display(draw=draw)

    def press_select(self):
        if self._cur_pos == -1:
            GPIO.cleanup()
            sys.exit(0)

        else:
            selected_day = self._days[self._page_idx * Display.max_lines:][self._cur_pos]
            print(f"Selected: {selected_day}")

    def exec_loop(self):
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


if __name__ == "__main__":

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

    display = Display(days=days)
    display.exec_loop()
