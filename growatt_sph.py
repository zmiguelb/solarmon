import datetime
from pymodbus.exceptions import ModbusIOException

# Codes
StateCodes = {
    0: 'Waiting',
    1: 'Normal',
    3: 'Fault'
}

ErrorCodes = {
    0: 'None',
    24: 'Auto Test Failed',
    25: 'No AC Connection',
    26: 'PV Isolation Low',
    27: 'Residual Current High',
    28: 'DC Current High',
    29: 'PV Voltage High',
    30: 'AC Voltage Outrange',
    31: 'AC Freq Outrange',
    32: 'Module Hot'
}

for i in range(1, 24):
    ErrorCodes[i] = "Error Code: %s" % str(99 + i)

DeratingMode = {
    0: 'No Deratring',
    1: 'PV',
    2: '',
    3: 'Vac',
    4: 'Fac',
    5: 'Tboost',
    6: 'Tinv',
    7: 'Control',
    8: '*LoadSpeed',
    9: '*OverBackByTime',
}

def read_single(row, index, unit=10):
    return float(row.registers[index]) / unit

def read_double(row, index, unit=10):
    return float((row.registers[index] << 16) + row.registers[index + 1]) / unit

def merge(*dict_args):
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result

class Growatt:
    def __init__(self, client, name, unit):
        self.client = client
        self.name = name
        self.unit = unit

        self.read_info()

    def read_info(self):
        row = self.client.read_holding_registers(88, unit=self.unit)
        if type(row) is ModbusIOException:
            raise row

        self.modbusVersion = row.registers[0]/100

    def print_info(self):
        print('Growatt:')
        print('\tName: ' + str(self.name))
        print('\tUnit: ' + str(self.unit))
        print('\tModbus Version: ' + str(self.modbusVersion))

    def read(self):
        row = self.client.read_input_registers(0, 94, unit=self.unit)
        if type(row) is ModbusIOException:
            return None

        # http://www.growatt.pl/dokumenty/Inne/Growatt%20PV%20Inverter%20Modbus%20RS485%20RTU%20Protocol%20V3.04.pdf
        #                                           # Unit,     Variable Name,      Description
        info = {                                    # ==================================================================
            #'StatusCode': row.registers[0],         # N/A,      Inverter Status,    Inverter run state
            #'Status': StateCodes[row.registers[0]],
            'Ppv': read_double(row, 1),             # 0.1W,     Ppv H,              Input power (high)
                                                    # 0.1W,     Ppv L,              Input power (low)
            'Vpv1': read_single(row, 3),            # 0.1V,     Vpv1,               PV1 voltage
            'PV1Curr': read_single(row, 4),         # 0.1A,     PV1Curr,            PV1 input current
            'PV1Watt': read_double(row, 5),         # 0.1W,     PV1Watt H,          PV1 input watt (high)
                                                    # 0.1W,     PV1Watt L,          PV1 input watt (low)
            'Vpv2': read_single(row, 7),            # 0.1V,     Vpv2,               PV2 voltage
            'PV2Curr': read_single(row, 8),         # 0.1A,     PV2Curr,            PV2 input current
            'PV2Watt': read_double(row, 9),         # 0.1W,     PV2Watt H,          PV2 input watt (high)
                                                    # 0.1W,     PV2Watt L,          PV2 input watt (low)
            'Pac': read_double(row, 35),            # 0.1W,     Pac H,              Output power (high)
                                                    # 0.1W,     Pac L,              Output power (low)
            'Fac': read_single(row, 37, 100),       # 0.01Hz,   Fac,                Grid frequency
            'Vac1': read_single(row, 38),           # 0.1V,     Vac1,               Three/single phase grid voltage
            'Iac1': read_single(row, 39),           # 0.1A,     Iac1,               Three/single phase grid output current
            'Pac1': read_double(row, 40),           # 0.1VA,    Pac1 H,             Three/single phase grid output watt (high)
 
            'EnergyToday': read_double(row, 53),    # 0.1kWh,   Energy today H,     Today generate energy (high)
                                                    # 0.1kWh,   Energy today L,     Today generate energy today (low)
            'EnergyTotal': read_double(row, 55),    # 0.1kWh,   Energy total H,     Total generate energy (high)
                                                    # 0.1kWh,   Energy total L,     Total generate energy (low)
            'TimeTotal': read_double(row, 57, 2),   # 0.5S,     Time total H,       Work time total (high)
                                                    # 0.5S,     Time total L,       Work time total (low)
            'Temp': read_single(row, 93)            # 0.1C,     Temperature,        Inverter temperature
        }
        
 #       # Battery data
 #       row = self.client.read_input_registers(1000, 8, unit=self.unit)
 #       info = merge(info, {
 #           'BatPDischarge': read_double(row, 9),   # 0.1W,   Pdischarge1  H,     Discharge power (high)
 #                                                   # 0.1W,   Pdischarge1  L,     Discharge power (low)
 #           'BatPCharge': read_double(row, 11),     # 0.1W,   Pcharge1  H,        Charge power (high)
 #                                                   # 0.1W,   Pcharge1  L,        Charge power (low)
 #           'BatVolt': read_single(row, 13),        # 0.1V,   Vbat,               Battery voltage
 #           'BatSOC': read_single(row, 14),         # 1%,     SOC,                State of charge Capacity
 #           'AC2Grid': read_double(row, 29),        # 0.1W,   Pactogrid total H,  AC power to grid total (high)
 #                                                   # 0.1W,   Pactogrid total L,  AC power to grid total (low)
 #           'Inv2Load': read_double(row, 37),       # 0.1W,   PLocalLoad total H, INV power to local load total (high)
 #                                                   # 0.1W,   PLocalLoad total L, INV power to local load total (low)
 #           'BatTemp': read_single(row, 40)         # 1%,     Battery Temperature,Battery Temperature
 #       })

        # UPS information (offline)
#        row = self.client.read_input_registers(1067, 8, unit=self.unit)
#        info = merge(info, {
#            'EPSFAC': read_single(row, 0, 100),     # 0.01Hz,  EPS Fac,     UPSfrequency
#            'EPSVac1': read_single(row, 1),         # 0.1V,    EPS Vac1,    UPS phase R output voltage
#            'EPSIac1': read_single(row, 2),         # 0.1V,    EPS Iac1,    UPS phase R output current      
#            'EPSPac1': read_double(row, 3),         # 0.1VA,   EPS Pac1 H,  UPS phase R output power (high)      
#                                                    # 0.1VA,   EPS Pac1 L,  UPS phase R output power (low) 
#            'EPSLoadPer': read_single(row, 14)      # 1%,      Loadpercent, Load percent of UPS ouput
#        
#        })

        return info
