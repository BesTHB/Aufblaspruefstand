# This is a MicroPython script for the Pi Pico.
# It reads an analog input on GPIO26 (analog pin A0),
# prints it and sleeps 0.2s until repeating.

from machine import ADC
from utime import sleep_ms

sensor = ADC(26)   # GP26 -> A0

while True:
    print(sensor.read_u16())    # read analog input (will come as an unsigned 16-bit integer, which ranges from 0-65535 !)
    sleep_ms(200)               # sleep 0.2s