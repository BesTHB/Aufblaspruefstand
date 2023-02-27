import serial
import matplotlib.pyplot as plt
from datetime import datetime

try:
    port = 'COM4'
    ser = serial.Serial(port, 9600)

    v_in = 3.3   # input voltage in V
    start_time = datetime.now()  # store start time

    vals_time = []
    vals_pressure = []

    while True:
        sensorVal = int(str(ser.readline(), 'UTF-8').rstrip('\n'))   # read serial, convert to string as UTF-8, rstrip newline-character, convert to int
        voltage = sensorVal*v_in/(2**16)
        p_psi = 2.5*voltage - 1.25
        p_mbar = 68.9476*p_psi
        print(f'16bit input = {sensorVal}, V = {voltage:.3f}, psi = {p_psi}, mbar = {p_mbar}')

        dt = datetime.now() - start_time

        vals_pressure.append(p_mbar)
        vals_time.append(dt.total_seconds())

        plt.cla()
        plt.axis([0, 360, 0, 100])
        plt.plot(vals_time, vals_pressure)
        plt.xlabel('Versuchslaufzeit / s')
        plt.ylabel('Druck im Luftballon / mbar')
        plt.pause(0.001)

except serial.serialutil.SerialException:
    print(f'Kein Gerät unter {port} gefunden.')

except KeyboardInterrupt:
    print('Abbruch durch User')