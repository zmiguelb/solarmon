#!/usr/bin/env python3

import time
import os

from configparser import RawConfigParser
from influxdb import InfluxDBClient
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
import paho.mqtt.client as mqtt

#from growatt import Growatt
from growatt_sph import Growatt


settings = RawConfigParser()
settings.read(os.path.dirname(os.path.realpath(__file__)) + '/solarmon.cfg')

interval = settings.getint('query', 'interval', fallback=1)
offline_interval = settings.getint('query', 'offline_interval', fallback=60)
error_interval = settings.getint('query', 'error_interval', fallback=60)

db_name = settings.get('influx', 'db_name', fallback='inverter')
measurement = settings.get('influx', 'measurement', fallback='inverter')

#MQTT
print('Setup MQTT Client... ', end='')
mqtt_port = settings.getint('mqtt', 'port', fallback=1883)
mqtt_host = settings.get('mqtt', 'host', fallback='localhost')
mqtt_client_name = settings.get('mqtt', 'client_name', fallback= os.uname()[1])
mqtt_keepalive = settings.getint('mqtt', 'keepalive', fallback=180)
topic_solar_kwh = settings.get('mqtt', 'kwh_solar_topic', fallback='')
topic_solar_watt = settings.get('mqtt', 'watt_solar_topic', fallback='')
topic_battery_soc = settings.get('mqtt', 'soc_battery_topic', fallback='')
topic_battery_watt = settings.get('mqtt', 'watt_battery_topic', fallback='')


def on_publish(client,userdata,result):                     #create function for publishing callback
    #print("data published")
    pass


mqtt_client = mqtt.Client(client_id=mqtt_client_name)
mqtt_client.on_publish = on_publish                          #assign function to callback
mqtt_client.connect(mqtt_host, mqtt_port, mqtt_keepalive)
mqtt_client.loop_start()
print('Done!')



# Clients
print('Setup InfluxDB Client... ', end='')
influx = InfluxDBClient(host=settings.get('influx', 'host', fallback='localhost'),
                        port=settings.getint('influx', 'port', fallback=8086),
                        username=settings.get('influx', 'username', fallback=None),
                        password=settings.get('influx', 'password', fallback=None),
                        database=db_name)
influx.create_database(db_name)
print('Done!')

print('Setup Serial Connection... ', end='')
port = settings.get('solarmon', 'port', fallback='/dev/ttyUSB0')
client = ModbusClient(method='rtu', port=port, baudrate=9600, stopbits=1, parity='N', bytesize=8, timeout=1)
client.connect()
print('Dome!')

print('Loading inverters... ')
inverters = []

for section in settings.sections():
    if not section.startswith('inverters.'):
        continue

    name = section[10:]
    unit = int(settings.get(section, 'unit'))
    measurement = settings.get(section, 'measurement')
    growatt = Growatt(client, name, unit)
    growatt.print_info()
    inverters.append({
        'error_sleep': 0,
        'growatt': growatt,
        'measurement': measurement
    })
print('Done!')

while True:
    online = False
    for inverter in inverters:
        # If this inverter errored then we wait a bit before trying again
        if inverter['error_sleep'] > 0:
            inverter['error_sleep'] -= interval
            continue

        growatt = inverter['growatt']
        try:
            now = time.time()
            info = growatt.read()

            if info is None:
                continue

            # Mark that at least one inverter is online so we should continue collecting data
            online = True

            points = [{
                'time': int(now),
                'measurement': inverter['measurement'],
                "fields": info
            }]

            print(growatt.name)
            print(points)
            
            if not influx.write_points(points, time_precision='s'):
                print("Failed to write to DB!")
            #Publish solar/kwh
            if topic_solar_kwh:
                ret = mqtt_client.publish(topic_solar_kwh, info["EnergyToday"])
                print("Error code:"+str(ret[0])+"\tMessage ID:"+str(ret[1]))
            #Publish solar/watt
            if topic_solar_watt:
                ret = mqtt_client.publish(topic_solar_watt, info["Ppv"])
                print("Error code:"+str(ret[0])+"\tMessage ID:"+str(ret[1]))
            #Publish battery/kwh
            if topic_battery_soc:
                ret = mqtt_client.publish(topic_battery_soc, info["BatSOC"]*10)
                print("Error code:"+str(ret[0])+"\tMessage ID:"+str(ret[1]))
            #Publish battery/watt
            if topic_battery_watt:
                battery_total = info["BatPCharge"] - info["BatPDischarge"] 
                ret = mqtt_client.publish(topic_battery_watt, battery_total)
                print("Error code:"+str(ret[0])+"\tMessage ID:"+str(ret[1]))
        except Exception as err:
            print(growatt.name)
            print(err)
            inverter['error_sleep'] = error_interval

    if online:
        time.sleep(interval)
    else:
        # If all the inverters are not online because no power is being generated then we sleep for 1 min
        print("I am sleeping for "+str(offline_interval)+"...")
        time.sleep(offline_interval)
        print("Closing modbus connection...")
        client.close()
        time.sleep(offline_interval)
        print("Reconnecting modbus client ...")
        client.connect()
        print("Reconnected")
        print('Re-Loading inverters... ')
        inverters = []

        for section in settings.sections():
            if not section.startswith('inverters.'):
                continue

            name = section[10:]
            unit = int(settings.get(section, 'unit'))
            measurement = settings.get(section, 'measurement')
            growatt = Growatt(client, name, unit)
            growatt.print_info()
            inverters.append({
                'error_sleep': 0,
                'growatt': growatt,
                'measurement': measurement
            })
        print('Done!')
