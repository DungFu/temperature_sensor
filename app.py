import sqlite3

from datetime import datetime
from flask import Flask
from flask_table import Table, Col

database_file = 'data.db'

# Declare your table
class TempsTable(Table):
    temp_in = Col('Inside Temp')
    temp_out = Col('Outside Temp')
    date = Col('Date')

app = Flask(__name__)

@app.route("/")
def main():
    temps = []
    db = sqlite3.connect(database_file)
    cursor = db.cursor()
    cursor.execute('''
        SELECT * FROM Temps ORDER BY timestamp DESC LIMIT 120
    ''')
    current_temps = None
    for row in cursor:
        date = datetime.fromtimestamp(row[3]).strftime('%Y-%m-%d %H:%M:%S')
        temps.append(dict(temp_in=str(row[1]), temp_out=str(row[2]), date=date))
        if current_temps is None:
            current_temps = [str(row[1]), str(row[2])]
    table = TempsTable(temps)
    html = """
        <html>
            <head>
                <title>%s</title>
                <style>
                    body {
                        margin: 0;
                        text-align: center;
                    }
                    table {
                        color: #333;
                        font-family: Helvetica, Arial, sans-serif;
                        width: 100%%; 
                        border-collapse: collapse;
                        border-spacing: 0; 
                        margin: 0 auto;
                    }

                    td, th {  
                        border: 1px solid transparent;
                        height: 30px; 
                        transition: all 0.3s;
                    }

                    th {  
                        background: #DFDFDF;
                        font-weight: bold;
                    }

                    td {  
                        background: #FAFAFA;
                        text-align: center;
                    }

                    tr:nth-child(even) td { background: #F1F1F1; }   

                    tr:nth-child(odd) td { background: #FEFEFE; }  

                    tr td:hover { background: #666; color: #FFF; }  
                </style>
            </head>
            <body>
                <h1>Current Inside Temp: %s</h1>
                <h1>Current Outside Temp: %s</h1>
                %s
            </body>
        </html>
        """ % (
            "Temperature Sensor",
            "None" if current_temps is None else current_temps[0],
            "None" if current_temps is None else current_temps[1],
            table.__html__())
    return html

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
