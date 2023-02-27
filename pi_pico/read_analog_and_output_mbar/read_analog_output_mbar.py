import serial

try:
    port = 'COM4'
    ser = serial.Serial(port, 9600)

    v_in = 3.3   # input voltage in V

    while True:
        sensorVal = int(str(ser.readline(), 'UTF-8').rstrip('\n'))   # read serial, convert to string as UTF-8, rstrip newline-character, convert to int
        voltage = sensorVal*v_in/(2**16)
        p_psi = 2.5*voltage - 1.25
        p_mbar = 68.9476*p_psi
        print(f'16bit input = {sensorVal}, V = {voltage:.3f}, psi = {p_psi}, mbar = {p_mbar}')

except serial.serialutil.SerialException:
    print(f'Kein Gerät unter {port} gefunden.')

except KeyboardInterrupt:
    print('Abbruch durch User')