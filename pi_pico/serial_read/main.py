import sys
import select
import _thread
from machine import ADC, Pin
from utime import sleep_ms

# https://stackoverflow.com/questions/74390514/serial-communication-with-raspberry-pi-pico-and-python
# https://forums.raspberrypi.com/viewtopic.php?t=300474
# https://docs.micropython.org/en/latest/library/select.html

sensor = ADC(26)                 # GP26 -> A0
mv = Pin(9, Pin.OUT, value=0)    # GP9  -> Magnetventil
led = Pin(25, Pin.OUT, value=0)  # GP25 -> Onboard LED  (DEBUG)

def lesen():
    """
    Funktion, die in separatem Thread ausgefuehrt werden soll.
    """
    spoll = select.poll()
    spoll.register(sys.stdin, select.POLLIN)

    while True:
        res = spoll.poll()
        ch = res[0][0].read(1)
        if (ch == 'o'):
            led.on()   # debug
            mv.on()
        elif (ch == 'c'):
            led.off()  # debug
            mv.off()

# Funktion, die in separatem Thread neben dem Hauptprogramm gestartet wird
_thread.start_new_thread(lesen, ())

# Hauptprogramm
while True:
    print(sensor.read_u16())    # read analog input (will come as an unsigned 16-bit integer, which ranges from 0-65535 !)
    sleep_ms(100)               # sleep 0.2s