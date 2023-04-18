import serial
import time

try:
    port = 'COM6'
    ser = serial.Serial(port, 9600)

    while True:
        ser.write(b'o')
        time.sleep(1)
        ser.write(b'c')
        time.sleep(1)

except serial.serialutil.SerialException:
    print(f'Kein Gerät unter {port} gefunden.')

except KeyboardInterrupt:
    print('Abbruch durch User')