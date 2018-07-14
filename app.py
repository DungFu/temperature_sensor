import os
import pygal
import sqlite3
import time

from configparser import SafeConfigParser
from datetime import datetime
from flask import Flask, send_from_directory, render_template
from flask_table import Table, Col
from pygal.style import DefaultStyle

database_file = 'data.db'
config_file = 'config.ini'

# Declare your table
class TempsTable(Table):
    temp_in = Col('Inside Temp')
    temp_out = Col('Outside Temp')
    date = Col('Date')

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')

@app.route("/")
def main():
    temps = []
    config = SafeConfigParser()
    config.read('config.ini')
    fetch_hours = float(config.get('MAIN', 'WEB_UI_HOURS'))
    db = sqlite3.connect(database_file)
    cursor = db.cursor()
    cursor.execute('''
        SELECT * FROM Temps WHERE timestamp > ? ORDER BY timestamp DESC
    ''', (int(time.time()) - int(fetch_hours*60*60),))
    current_temps = None
    inside_temps = []
    outside_temps = []
    for row in cursor:
        date = datetime.fromtimestamp(row[3])
        date_string = date.strftime("%Y/%m/%d - %H:%M")
        inside_temps.append((date, row[1]))
        outside_temps.append((date, row[2]))
        if current_temps is None:
            current_temps = [str(row[1]), str(row[2])]
        temps.append(dict(temp_in=str(row[1]), temp_out=str(row[2]), date=date_string))
    table = TempsTable(temps)
    graph = pygal.DateTimeLine(
        width=1000,
        height=500,
        legend_at_bottom=True,
        show_dots=False,
        style=DefaultStyle,
        x_value_formatter=lambda dt: dt.strftime('%H:%M'))
    graph.add("Inside Temp (\u2109)",  inside_temps)
    graph.add("Outside Temp (\u2109)",  outside_temps)
    graph_data = graph.render_data_uri()
    return render_template(
        "index.html",
        inside_temp="None" if current_temps is None else current_temps[0],
        outside_temp="None" if current_temps is None else current_temps[1],
        graph_data=graph_data,
        table=table.__html__())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
