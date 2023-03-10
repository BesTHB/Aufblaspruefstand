import serial

try:
    port = 'COM4'
    ser = serial.Serial(port, 9600)

    while True:
        sensorVal = int(str(ser.readline(), 'UTF-8').rstrip('\n'))   # read 16bit serial value, convert to string as UTF-8, rstrip newline-character, convert to int
        print(f'16bit input = {sensorVal}')

except serial.serialutil.SerialException:
    print(f'Kein Gerät unter {port} gefunden.')

except KeyboardInterrupt:
    print('Abbruch durch User')