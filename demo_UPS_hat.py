import time

from INA219 import INA219

if __name__=='__main__':

    # Create an INA219 instance.
    ina219 = INA219(addr=0x43)
    while True:
        bus_voltage = ina219.getBusVoltage_V()             # voltage on V- (load side)
        shunt_voltage = ina219.getShuntVoltage_mV() / 1000 # voltage between V+ and V- across the shunt
        current = ina219.getCurrent_mA()                   # current in mA
        power = ina219.getPower_W()                        # power in W
        
        charge_perc = (bus_voltage - 3) / 1.2 * 100
        charge_perc = min(charge_perc, 100)
        charge_perc = max(charge_perc, 0)

        # INA219 measure bus voltage on the load side. So PSU voltage = bus_voltage + shunt_voltage
        print(f"PSU Voltage:   {bus_voltage + shunt_voltage:6.3f} V")
        print(f"Shunt Voltage: {shunt_voltage:9.6f} V")
        print(f"Load Voltage:  {bus_voltage:6.3f} V")
        print(f"Current:       {current/1000:6.3f} A")
        print(f"Power:         {power:6.3f} W")
        print(f"Percent:       {charge_perc:3.1f}%\n")

        time.sleep(2)