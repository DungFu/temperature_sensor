import glob
import os
import requests
import sqlite3
import time

from configparser import SafeConfigParser
from datetime import datetime
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
            return temp_f
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

def send_new_fan_state(plug, state):
    print('Turning the fan ' + state)
    if state is "ON":
        plug.turn_on()
    elif state is "OFF":
        plug.turn_off()
    db = sqlite3.connect(database_file)
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO Actions(state, timestamp) VALUES(?,?)
    ''', (state, int(time.time())))
    db.commit()

def fan_state_more_than_12_hours_ago(state):
    db = sqlite3.connect(database_file)
    cursor = db.cursor()
    cursor.execute('''
        SELECT MAX(timestamp) FROM Actions WHERE state=?
    ''', (state,))
    for row in cursor:
        timestamp = row[0]
        if timestamp is not None:
            return int(time.time()) - timestamp > (12 * 60 * 60)
    return True

def update_fan_state():
    maybe_create_table();
    ftemp_in = read_temp()
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
    fallback_temp_disable = float(config.get('MAIN', 'FALLBACK_TEMP_DISABLE'))

    db = sqlite3.connect(database_file)
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO Temps(ftemp_in, ftemp_out, timestamp) VALUES(?,?,?)
    ''', (ftemp_in, ftemp_out, int(time.time())))
    db.commit()
    
    for plug in Discover.discover().values():
        if (ftemp_in is not None):
            if (plug.state is not "ON" and
                datetime.now().hour >= 16 and
                ftemp_in > threshold_temp_high and
                ftemp_out < ftemp_in):
                send_new_fan_state(plug, "ON")
            elif (plug.state is not "OFF" and ftemp_in < threshold_temp_low):
                send_new_fan_state(plug, "OFF")
        else:
            if (plug.state is not "ON" and
                fan_state_more_than_12_hours_ago("ON") and
                datetime.now().hour >= 16 and
                ftemp_out_max > threshold_temp_high and
                ftemp_out < threshold_temp_high and
                ftemp_out > threshold_temp_low):
                send_new_fan_state(plug, "ON")
            elif (plug.state is not "OFF" and
                  fan_state_more_than_12_hours_ago("OFF") and
                  (ftemp_out < fallback_temp_disable or datetime.now().hour >= 23)):
                send_new_fan_state(plug, "OFF")

update_fan_state();
