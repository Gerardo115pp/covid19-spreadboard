from bs4 import BeautifulSoup as soup
from pandas import DataFrame, Series
from GeneralServerTools import getConnAndCursor, Sha1
from datetime import datetime
from time import time, mktime
from unicodedata import normalize
import lxml, requests, os, json, re

class ExtractorException(Exception):
    pass

class Extractor:
    def __init__(self):
        if not os.path.exists(os.path.join("operational_data", "extractor_data.json")):
            raise ExtractorException("operational_data or extractor_data were not found...")
        with open("operational_data/extractor_data.json") as f:
            self.data = json.load(f)
        self.__countries_need_stats = {'First outbreak', 'Index case', 'Arrival date'}
        self.__date_regex = re.compile(r"[a-zA-Z\d]+\s[a-zA-Z\d]+\s\d{4}")
        self.__static_data = "./data_sources/countries_static_data.json"
        self.__todays_wiki_data_path = f"./data_sources/wikidata/{datetime.now().strftime('%d-%m-%Y')}.json"
        self.numeric_regex = re.compile(r"^[\d,]+$")
        self.hasher = Sha1()

    
    #===================================
    #=            general              =
    #===================================
    
    def updateData(self):
        self.updateTests()
        current_static_data = self.getCurrentStaticData()
        mysql = getConnAndCursor("inserter", "covid19")
        if not os.path.exists(self.__todays_wiki_data_path):
            print(f"Creating data_source: {self.__todays_wiki_data_path}...")
            self.createWikipediaSource()
        with open(self.__todays_wiki_data_path) as f:
            wiki_data = json.load(f)
        print("Updating general Status...")
        self.updateGeneralStatus(wiki_data, current_static_data, mysql)
        print("Updating daily cases...")
        self.updateCasesData()
        self.insertDailyCases(current_static_data)
        print("Done")
        
        
    
    def updateGeneralStatus(self, wiki_data, countries_data, mysql):
        try:
            for country in wiki_data:
                if country not in countries_data:
                    continue
                uuid = self.hasher.get_hash(country + str(countries_data[country]['arrival_date']))
                sql = f"UPDATE `overall_status` SET total_deaths={wiki_data[country]['deaths']}, "    
                sql += f"total_recoverys={wiki_data[country]['recoverys']}, "
                sql += f"cases={wiki_data[country]['cases']}, "
                sql += f"tests_made={countries_data[country]['tests']} "
                sql += f"WHERE uuid='{uuid}' LIMIT 1;"
                mysql['cursor'].execute(sql)
                mysql['conn'].commit()
        except Exception as e:
            raise e
        finally:           
            mysql["conn"].close()
    def requestData(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        return False
    
    def getCurrentStaticData(self):
        if os.path.exists(self.__static_data):
            with open(self.__static_data) as f:
               data = json.load(f)
            return data
        else:
            raise ExtractorException(f"countries static data couldnt be found in '{self.__static_data}'...")
    
    def saveCurrentStaticData(self, new_data):
        if os.path.exists(self.__static_data):
            with open(self.__static_data, 'w') as f:
                json.dump(new_data, f, indent=4)
        else:
            raise ExtractorException(f"countries static data couldnt be found in '{self.__static_data}'...")
    #===================================
    #=            opendata             =
    #===================================
    
    def __formatOpendataResponse(self, response):
        print(f"{'='*30}\n\tDEPRECATED\n{'='*30}")
        response = json.loads(response.content)
        if "records" in response:
            countries = set()
            for record in response["records"]:
                if record['countriesAndTerritories'] not in countries:
                    countries.add(record['countriesAndTerritories'])
            countries = {c:[] for c in countries}
            for record in response["records"]:
                countries[record['countriesAndTerritories']].append(record)
                del record['countriesAndTerritories']
            return countries
        response = json.dumps(response)
        raise ExtractorException(f"Response from opendata was not valid:\n{response if len(response) < 100 else response[:100]}...")
                                  
    def updateOpendataSource(self):
        url = self.data["covid-opendata"]
        response = requests.get(url)
        print("updateing opendata: ", end="")
        if response.ok:    
            open_data = self.__formatOpendataResponse(response)
            with open("data_sources/opendata.json", 'w') as f:
                json.dump(open_data, f)
            print("success")
        else:
            print(f"fail request to '{url}' returned response with code {response.status_code}")
        return
    
    #===================================
    #=            wikipedia            =
    #===================================
    
    def __parseCountries(self, covid_container):
        countries_tags = covid_container.findAll("tr", {"class": ""})[1:]
        countries = {}
        for countrie in countries_tags:
            countrie_stats = countrie.findAll("td")
            countrie_name = normalize("NFKD",countrie.a.text).encode('ascii', 'ignore').decode('ascii') 
            countries[countrie_name.lower()] = {
                "flag": countrie.img['src'],
                "cases": countrie_stats[0].text,
                "deaths": countrie_stats[1].text,
                "recoverys": countrie_stats[2].text,
                "url": "https://en.wikipedia.org/" + countrie.a['href']
            }
        return self.__cleanWikipediaData(countries)
    
    def __cleanWikipediaData(self, countries):
        countries_dataframe = DataFrame.from_dict(countries, orient="index")
        
        #cleaning the rows
        for column in countries_dataframe:
            if column in ['flag', 'url']:
                continue
            countries_dataframe[column] = countries_dataframe[column].apply(lambda x: x if self.numeric_regex.match(x) else "-1")
            countries_dataframe[column] = countries_dataframe[column].apply(lambda x: int(x.replace('\n','').replace(',','').replace('—','0')))
        
        #saving data
        file_name = datetime.now().strftime("%d-%m-%Y")
        countries_json = countries_dataframe.to_dict(orient='index') 
        with open(f"data_sources/wikidata/{file_name}.json", 'w') as f:
            json.dump(countries_json, f, indent=4)
        return countries_json
    
    def createWikipediaSource(self):
        url = self.data["covid-wikipedia"]
        response = self.requestData(url) 
        if response:
            covid_container = soup(response, 'lxml').find("div", {"id": "covid19-container"})
            return self.__parseCountries(covid_container)
        else:
            raise print(f"fail request to '{url}' was rejected")
    
    def extractStaticData(self, url):
        response = requests.get(url)
        print("Parsing data...")
        tiempo = time()
        if response.ok:
            data_soup = soup(response.content, 'lxml')
            infobox = data_soup.find('table', {'class': 'infobox'})
            countrie_stats = infobox.findAll('tr')
            countrie_static_data = {}
            for stat in countrie_stats:
                if not stat.th:
                    continue
                if stat.th.text in self.__countries_need_stats:
                    countrie_static_data[stat.th.text] = stat.td.text
            if len(countrie_static_data) != len(self.__countries_need_stats):
                for stat in self.__countries_need_stats:
                    if stat not in countrie_static_data:
                        countrie_static_data[stat] = "unknown"
            print(f"Finished parsing in {time() - tiempo}")
            return self.__transformStaticData(countrie_static_data)
        raise ExtractorException(f"request to '{url}' responded with status code: {response.status_code}")
    
    def __convertArrivalDateToTimestamp(self, time_string):
        print(f"time_string: '{time_string}'")
        time_string = time_string.strip()
        if re.match(r"^\d{1,2}\s[A-Za-z]+\s\d\d\d\d$", time_string):
            format_string = "%d %B %Y"
        elif re.match(r"^[A-Za-z]+\s\d{1,2}\s\d\d\d\d$", time_string):
            format_string = "%B %d %Y"
        else:
            raise ExtractorException(f"time string '{time_string}' doesnt match any of the established formats")
        return mktime(datetime.strptime(time_string , format_string).timetuple())
    
    def __transformStaticData(self, countries_static_data):
        if countries_static_data['First outbreak'] != "unknown":
            #removes de '(locals)' and '(globals)' substrings or any similar
            countries_static_data['First outbreak'] = ','.join(re.split(r"\([a-zA-Z\d]+\)", countries_static_data['First outbreak']))
            #removes the coordenates part of the string, may want to change that later
            countries_static_data['First outbreak'] = re.split(r"\d" ,countries_static_data['First outbreak'], 1)[0]
            #gets a list with the city names
            countries_static_data['First outbreak'] = list(filter(lambda x: x != '',re.split(r"\s?,\s?",countries_static_data['First outbreak'])))
        if countries_static_data['Arrival date'] != "unknown":
            countries_static_data['Arrival date'] = re.split(r'[\(\[]', countries_static_data['Arrival date'], 1)[0]
            # removes '–' char found in some countries
            if countries_static_data['Arrival date'].find('–') !=  -1:
                countries_static_data['Arrival date'] = self.__date_regex.search(countries_static_data['Arrival date']).group(0)
            #removes comas if present
            countries_static_data['Arrival date'] = countries_static_data['Arrival date'].replace(',', '')
            countries_static_data['Arrival date'] = self.__convertArrivalDateToTimestamp(countries_static_data['Arrival date'])
        return countries_static_data
    
    def createStaticDataFile(self):
        if os.path.exists("data_sources/29-04-2020.json"):
            with open("data_sources/29-04-2020.json", 'r') as f:
                countries_data = json.load(f)
            countries_static_data = {}
            for countrie in countries_data:
                print(f"Getting static data of {countrie}...")
                countries_static_data[countrie] = self.extractStaticData(countries_data[countrie]["url"])
            with open("data_sources/countries_static_data.json", 'w') as f:
                json.dump(countries_static_data, f, indent=4)
            return countries_static_data
    
    #===================================
    #=            postman              =
    #===================================
    
    def getCountryStatsBySlug(self, slug):
        url = f"https://api.covid19api.com/dayone/country/{slug}"
        return self.requestData(url)
    
    def __getCountrysDataFromPostman(self):
        url = self.data["covid-tests"]
        data = self.requestData(url)
        if data:
            return json.loads(data)
        raise ExtractorException("Tests api is down...")
    
    def updateTests(self):
        print("Updating tests data")
        data = self.requestData(self.data['covid-tests'])
        if data:
            data = json.loads(data)
            static_data = self.getCurrentStaticData()
            static_data_dataframe = DataFrame.from_dict(static_data, orient='index')
            for country_data in data:
                if country_data['countryInfo']['iso2'] in static_data_dataframe.cca2.unique():
                    static_data_dataframe.loc[static_data_dataframe['cca2'] == country_data['countryInfo']['iso2'], 'tests'] = country_data['tests']
            static_data = static_data_dataframe.to_dict(orient='index')
            self.saveCurrentStaticData(static_data)
        else:
            raise ExtractorException("Request data for test was not accepted")
        
    def __saveSlugData(self, country_name, data):
        if not os.path.exists(f'./data_sources/countries_data/{country_name}'):
            os.mkdir(f'./data_sources/countries_data/{country_name}')
        for day in data:
            file_name = day["Date"].split('T')[0]
            if os.path.exists(f'./data_sources/countries_data/{country_name}/{file_name}.json'):
                continue
            with open(f'./data_sources/countries_data/{country_name}/{file_name}.json', 'w') as f:
                json.dump(day, f, indent=4)
    
    def addLocations(self):
        static_data = self.getCurrentStaticData()
        if 'long' not in static_data['israel']:
            static_dataframe = DataFrame.from_dict(static_data, orient='index')
            static_dataframe['long'] = -1.0
            static_dataframe['lat'] = -1.0
            api_data = self.__getCountrysDataFromPostman()
            for country in api_data:
                print(f"Adding location to '{country['country']}'...")
                if country['countryInfo']['iso2'] in static_dataframe.cca2.unique():
                    static_dataframe.loc[static_dataframe.cca2 == country['countryInfo']['iso2'], 'long'] = country['countryInfo']['long']
                    static_dataframe.loc[static_dataframe.cca2 == country['countryInfo']['iso2'], 'lat'] = country['countryInfo']['lat']
            static_data = static_dataframe.to_dict(orient='index')
            self.saveCurrentStaticData(static_data)
                                    
    def updateCasesData(self):
        static_data = self.getCurrentStaticData()
        for country in static_data:
            print(f"Getting data from '{country}'")
            if "missing" == static_data[country]["slug"]:
                print(f"Skiping {country}...")
                continue
            country_data = self.getCountryStatsBySlug(static_data[country]["slug"])
            country_data = json.loads(country_data)
            self.__saveSlugData(country, country_data)

    #===================================
    #=            mysql                =
    #===================================

    def insertStaticData(self):
        data = self.getCurrentStaticData()
        mysql = getConnAndCursor('inserter', 'covid19')
        try:
            print("Inserting static data...")
            for country in data:
                sql = "INSERT INTO `countries`(uuid, country_name, population, cca2, cca3, ccn3, hospibed_per_kp, slug, latitud, longitud) VALUES ("
                sql += f"'{self.hasher.get_hash(country + str(data[country]['long']) + str(data[country]['lat']))}', "
                sql += f"'{country}', "
                sql += f"{data[country]['population']}, "
                sql += f"'{data[country]['cca2']}', "
                sql += f"'{data[country]['cca3']}', "
                sql += f"{data[country]['ccn3']}, "
                sql += f"{data[country]['hospital_bed']}, "
                sql += f"'{data[country]['slug']}', "
                sql += f"{data[country]['long']}, "
                sql += f"{data[country]['lat']}"
                sql += ");"
                print(sql)
                mysql['cursor'].execute(sql)
                mysql['conn'].commit()
        except Exception as e:
            raise e
        finally:
            mysql['conn'].close()
    
    def __getCurrentCountriesStatus(self):
        file_name = datetime.now().strftime("%d-%m-%Y")
        if not os.path.exists(f"./data_sources/wikidata/{file_name}.json"):
            self.createWikipediaSource()
        with open(f"./data_sources/wikidata/{file_name}.json") as f:
            data = json.load(f)
        return data       
    
    def insertStatus(self):
        status_data = self.__getCurrentCountriesStatus()
        countrys_data = self.getCurrentStaticData()
        mysql = getConnAndCursor("inserter", "covid19")
        try:
            for country in status_data:
                if country not in countrys_data:
                    continue
                arrival = datetime.fromtimestamp(countrys_data[country]['arrival_date']) if countrys_data[country]['arrival_date'] != 0 else 'NULL'
                uuid = self.hasher.get_hash(country + str(countrys_data[country]['arrival_date']))
                sql = "INSERT INTO `overall_status`(uuid, cases, total_recoverys, total_deaths, tests_made, arrival, index_case) VALUES ("
                sql += f"'{uuid}', "
                sql += f"{status_data[country]['cases']}, "
                sql += f"{status_data[country]['recoverys']}, "
                sql += f"{status_data[country]['deaths']}, "
                sql += f"{countrys_data[country]['tests']}, "
                sql += f"'{arrival}', " if arrival != "NULL" else f"{arrival}, "
                sql += f"'{countrys_data[country]['index_case']}'"
                sql += ");"
                print(sql)
                mysql["cursor"].execute(sql)
                mysql["conn"].commit()
                mysql["cursor"].execute(f"UPDATE `countries` SET overall_status='{uuid}' WHERE uuid='{self.hasher.get_hash(country + str(countrys_data[country]['long']) + str(countrys_data[country]['lat']))}';")
                mysql["conn"].commit()
        except Exception as e:
            raise e
        finally:
            mysql['conn'].close()
    
    def __getDailyCasesUuids(self):
        mysql = getConnAndCursor("inserter", "covid19")
        try:
            mysql["cursor"].execute(f"SELECT uuid FROM `daily_cases`;")
            daily_cases = [row['uuid'] for row in mysql["cursor"].fetchall()]
            return daily_cases
        except Exception as e:
            raise e
        finally:
            mysql['conn'].close()
    
    def __getCountryUuid(self, country_name, country_data):
        return self.hasher.get_hash(country_name + str(country_data['long']) + str(country_data['lat']))
    
    def insertDailyCases(self, data=None):
        data = data if data else self.getCurrentStaticData()
        countries_path = "./data_sources/countries_data/"
        daily_cases = set(self.__getDailyCasesUuids())
        #self.updateCasesData()
        mysql = getConnAndCursor('inserter', 'covid19')
        try:    
            for country in data:
                if not os.path.exists(os.path.join(countries_path, country)):
                    print(f"Skipping {country}...")
                    continue
                print(f"Updating cases of {country}...")
                for case in os.scandir(os.path.join(countries_path, country)):
                    if case.name == '0001-01-01.json':
                        continue
                    uuid = self.hasher.get_hash(case.name + country)
                    if uuid in daily_cases:
                        continue
                    with open(case.path) as f:
                        case_data = json.load(f)
                    if not case_data:
                        continue
                    country_uuid = self.__getCountryUuid(country, data[country]) 
                    sql = "INSERT INTO `daily_cases`(uuid, date, cases, deaths, recoverys, country) VALUES ("
                    sql += f"'{uuid}', "
                    sql += f"'{case_data['Date'].replace('T',' ').replace('Z',' ')}', "
                    sql += f"{case_data['Confirmed']}, "
                    sql += f"{case_data['Deaths']}, "
                    sql += f"{case_data['Recovered']}, "
                    sql += f"'{country_uuid}'"
                    sql += ");"
                    mysql["cursor"].execute(sql)
                    mysql["conn"].commit()
        except Exception as e:
            raise e
        finally:
            mysql['conn'].close()
    
    def relateInfections(self):
        countrys_data = self.getCurrentStaticData()
        querys = []
        for country in countrys_data:
            print(f"getting infectors of {country}")
            if countrys_data[country]['first_outbreak'] != "unknown":
                for infector in countrys_data[country]['first_outbreak']:
                    infector_uuid = self.__getCountryUuid(infector, countrys_data[infector])
                    infected_uuid = self.__getCountryUuid(country, countrys_data[country])
                    sql = f"INSERT INTO `infectedinfector`(infected, infector) VALUES ('{infected_uuid}', '{infector_uuid}');"
                    querys.append(sql)
        mysql = getConnAndCursor('inserter', 'covid19')
        try:
            points = 1
            for sql in querys:
                print(f"\rInserting data{'.'*(points%3)}", end='')
                mysql["cursor"].execute(sql)
                mysql["conn"].commit()
                points += 1
        except Exception as e:
            print(f"Error on query: {sql}")
            raise e
        finally:
            mysql["conn"].close()
            print('\n') 
             
       
# os.chdir("server")
# e = Extractor()
# e.insertDailyCases()          
            
            
        
