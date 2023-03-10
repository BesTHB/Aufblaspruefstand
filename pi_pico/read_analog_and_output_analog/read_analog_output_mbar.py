import serial

try:
    port = 'COM4'
    ser = serial.Serial(port, 9600)

    v_in = 3.3      # input voltage in V
    v_0  = v_in/10  # voltage at  0psi (10% of v_in)
    v_10 = v_in-v_0 # voltage at 10psi (90% of v_in)

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

except serial.serialutil.SerialException:
    print(f'Kein Gerät unter {port} gefunden.')

except KeyboardInterrupt:
    print('Abbruch durch User')