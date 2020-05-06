from flask import Flask, request
from flask_cors import CORS
from Datagetters import CovidDatagetter

covid_datagetter = CovidDatagetter()
app = Flask(__name__, static_url_path='')
CORS(app)

@app.route('/covid19', methods=['POST'])
def getCountriesData():
    return covid_datagetter.getCountriesData()

@app.route("/infectors/<country_uuid>")
def getCountrysInfectors(country_uuid):
    return covid_datagetter.getCountriesExtraData(country_uuid)
    
if __name__ == "__main__":
    app.run("127.0.0.1", debug=True)