import fcntl
import io
import time

I2C_SLAVE = 0x0703

def read_pressure():
    try:
        with io.open("/dev/i2c-2", "rb+", buffering=0) as f:
            fcntl.ioctl(f, I2C_SLAVE, 0x50)

            # Write to config register
            f.write(bytes([0x02, 0x20]))
            time.sleep(0.1)  # Give some time for the device to process

            # Read from result register
            f.write(bytes([0x00]))
            result = f.read(2)

            # Process the result
            raw = (result[0] << 8 | result[1]) & 0xFFF
            voltage = (raw / 4096.0) * 3.3  # Assuming 3.3V reference
            pressure = voltage * (2000.0 / 5.0)  # Adjust this calculation as needed

            return pressure
    except IOError as e:
        print("Error: " + repr(e))
        return None
    except Exception as e:
        print("Error: " + repr(e))
        return None

# Test the function
pressure = read_pressure()
if pressure is not None:
    print("Pressure: " + str(pressure))
else:
    print("Failed to read pressure")
