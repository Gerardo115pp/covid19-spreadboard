from GeneralServerTools import getConnAndCursor
import json

class CovidDatagetter:
    def requestToDB(self, sql):
        mysql = getConnAndCursor("inserter", "covid19")
        try:
            mysql["cursor"].execute(sql)
            data = mysql["cursor"].fetchall()
            return data
        except Exception as e:
            raise e
        finally:
            mysql['conn'].close()
            
    def __convertArrivalsToSTR(self, country_data):
        country_data['arrival'] = country_data['arrival'].strftime("%d-%m-%Y") if country_data['arrival'] else "unknown"
        return country_data

    def getCountryInfectors(self, uuid):
        sql = f"SELECT countries.country_name FROM countries, infectedinfector WHERE countries.uuid=infectedinfector.infector AND infectedinfector.infected='{uuid}';"
        mysql = getConnAndCursor("inserter", "covid19")
        try:
            mysql["cursor"].execute(sql)
            return [result['country_name'] for result in mysql["cursor"].fetchall()]
        except Exception as e:
            raise e
        finally:
            mysql["conn"].close()

    def getCountriesData(self):
        data = self.requestToDB(f"SELECT countries.uuid, countries.country_name, countries.population, countries.hospibed_per_kp, countries.latitud, countries.longitud, overall_status.cases, overall_status.tests_made, overall_status.total_recoverys, overall_status.total_deaths, overall_status.arrival, overall_status.index_case FROM countries JOIN overall_status ON countries.overall_status=overall_status.uuid ORDER BY countries.country_name;")
        data = list(map(self.__convertArrivalsToSTR, data))
        return json.dumps(data)
    
    def getDailyInfections(self, country_uuid):
        mysql = getConnAndCursor('inserter', 'covid19')
        try:
            mysql['cursor'].execute(f"SELECT date, cases, deaths, recoverys FROM daily_cases WHERE country='{country_uuid}' ORDER BY date;")
            results = mysql['cursor'].fetchall()
            return results
        except Exception as e:
            raise e
        finally:
            mysql['conn'].close()    
            
    def getCountriesExtraData(self, uuid):
        data = {
            'infectors': self.getCountryInfectors(uuid),
            'daily_cases': self.getDailyInfections(uuid)
        }
        return data