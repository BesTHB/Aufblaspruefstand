import serial
import matplotlib.pyplot as plt
from datetime import datetime

try:
    port = 'COM4'
    ser = serial.Serial(port, 9600)

    v_in = 3.3                   # input voltage in V
    v_0  = v_in/10               # voltage at  0psi (10% of v_in)
    v_10 = v_in-v_0              # voltage at 10psi (90% of v_in)
    start_time = datetime.now()  # store start time

    vals_time = []
    vals_pressure = []

    while True:
        # read 16bit serial value, convert to string as UTF-8, rstrip newline-character and ...
        try:
            # convert to int
            sensorVal = int(str(ser.readline(), 'UTF-8').rstrip('\n'))
        except ValueError:
            # convert to float
            sensorVal = float(str(ser.readline(), 'UTF-8').rstrip('\n'))
        
        # convert 16bit integer to Volt
        voltage = sensorVal*v_in/(2**16)
        
        # convert Volt to psi (0.1*v_in == v_0 == 0psi ; 0.9*v_in == v_10 == 10psi)
        m = 10/(v_10-v_0)
        b = -v_0*m
        p_psi = m*voltage + b

        # convert psi to mbar
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