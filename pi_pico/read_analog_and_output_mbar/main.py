from machine import Pin, ADC
from time import sleep

sensor = ADC(26)   # GP26 -> A0
v_in = 3.3         # input voltage / V

while True:
    sensorVal = sensor.read_u16()    # read analog input (will come as an unsigned 16-bit integer, which ranges from 0-65535 !)
    voltage = sensorVal*v_in/65536   # convert the input signal to a voltage, assuming the pico is powered with v_in
    p_psi = 2.5*voltage - 1.25       # convert the voltage to a pressure (psi)
    p_mbar = 68.9476*p_psi           # convert the pressure from psi to mbar

    print(f'16-bit input: {sensorVal}, V = {voltage}, psi = {p_psi}, mbar = {p_mbar}')

    sleep(1)  # sleep 1s