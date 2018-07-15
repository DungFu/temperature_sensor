import glob
import os
import requests
import sqlite3
import time

from configparser import SafeConfigParser
from datetime import datetime
from decimal import Decimal
from pyHS100 import Discover

database_file = 'data.db'
config_file = 'config.ini'

def read_temp_raw(device_file):
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def read_temp():
    try:
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')

        base_dir = '/sys/bus/w1/devices/'
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/w1_slave'

        lines = read_temp_raw(device_file)
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = read_temp_raw()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            temp_f = temp_c * 9.0 / 5.0 + 32.0
            return float("{0:.2f}".format(temp_f))
        else:
            return None;
    except:
        return None;

def maybe_create_table():
    db = sqlite3.connect(database_file)
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Temps(id INTEGER PRIMARY KEY, ftemp_in REAL, ftemp_out REAL, timestamp INTEGER)
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Actions(id INTEGER PRIMARY KEY, state text, timestamp INTEGER)
    ''')
    db.commit()

def print_db():
    db = sqlite3.connect(database_file)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM Temps")
    print(cursor.fetchall())
    db.commit()

def send_new_fan_state(plug, state, now):
    print('Turning the fan ' + state)
    if state is "ON":
        plug.turn_on()
    elif state is "OFF":
        plug.turn_off()
    db = sqlite3.connect(database_file)
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO Actions(state, timestamp) VALUES(?,?)
    ''', (state, now))
    db.commit()

def update_fan_state():
    maybe_create_table();
    ftemp_in = read_temp()
    if ftemp_in is None:
        return
    print('ftemp_in', ftemp_in)

    config = SafeConfigParser()
    config.read('config.ini')

    PARAMS = {
        'lat': config.get('MAIN', 'LAT'),
        'lon': config.get('MAIN', 'LON'),
        'units': 'imperial',
        'APPID': config.get('MAIN', 'API_KEY')
    }

    r = requests.get(url = 'http://api.openweathermap.org/data/2.5/weather', params = PARAMS)
    ftemp_out = r.json()['main']['temp']
    ftemp_out_max = r.json()['main']['temp_max']
    print('ftemp_out', ftemp_out)

    threshold_temp_low = float(config.get('MAIN', 'THRESHOLD_TEMP_LOW'))
    threshold_temp_high = float(config.get('MAIN', 'THRESHOLD_TEMP_HIGH'))
    temp_delta_in_out = float(config.get('MAIN', 'TEMP_DELTA_IN_OUT'))

    now = int(time.time())

    db = sqlite3.connect(database_file)
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO Temps(ftemp_in, ftemp_out, timestamp) VALUES(?,?,?)
    ''', (ftemp_in, ftemp_out, now))
    db.commit()
    
    for plug in Discover.discover().values():
        if (plug.state is not "ON"
            and ftemp_in > threshold_temp_high
            and ftemp_out < ftemp_in - temp_delta_in_out):
            send_new_fan_state(plug, "ON", now)
        elif (plug.state is not "OFF"
              and (ftemp_in < threshold_temp_low or ftemp_out > ftemp_in - temp_delta_in_out)):
            send_new_fan_state(plug, "OFF", now)

update_fan_state();
