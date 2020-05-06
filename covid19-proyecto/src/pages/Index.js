import React, { Component } from 'react';
import { server_name } from '../serverInfo';
import '../css/index.css';

class MainPage extends Component
{

    state = {
        countries_info: {}
    }

    prepareCountriesData = data => {
        const { countries_info:clean_data } = this.state; 
        for(let country of data)
        {
            clean_data[country.country_name] = {
                ...country
            }
            delete clean_data[country.country_name].country_name;
            clean_data[country.country_name]['infectors'] = []; 
            clean_data[country.country_name]['daily_cases'] = []; 
            clean_data[country.country_name]['showing_extra'] = false;
        }
        this.setState({
            countries_info: clean_data
        });
    }

    componentWillMount()
    {
        if(Object.keys(this.state.countries_info).length === 0)
        {
            const request = new Request(`${server_name}/covid19`, {method:'POST'})
            fetch(request)
                .then(promise => promise.json())
                .then(response => {
                    this.prepareCountriesData(response);
                })
        }
    }

    formatBigNumber = big_num => {
        let big_num_f = big_num.toString();
        big_num_f = [...big_num_f].reverse().join('')
        return big_num_f.match(/\d{1,3}/g).join(',').split('').reverse().join('')
    }

    checkMissingData = num => {
        return  num > -1 ? num : "No Data";
    }

    showHiddenData = e => {
        const { currentTarget } = e;
        const { countries_info } = this.state;
        const country_name = currentTarget.querySelector('.country-name').innerText.toLowerCase(),
              extra_info = currentTarget.querySelector('.extra-info');
        if(this.state.countries_info[country_name].infectors.length === 0)
        {
            fetch(`${server_name}/infectors/${countries_info[country_name].uuid}`)
                .then(promise => promise.json())
                .then(response => {
                    countries_info[country_name].infectors = response.infectors;
                    countries_info[country_name].daily_cases = response.daily_cases;
                    this.setState({
                        countries_info
                    })
                })
        }
        extra_info.style.display = countries_info[country_name].showing_extra ? 'none' : 'flex';
        this.state.countries_info[country_name].showing_extra = !countries_info[country_name].showing_extra;
    }

    formatInfectors = infectors => {
        let infectors_string = "";
        infectors.forEach((infector, h) => {
            infectors_string += 1 === infectors.length || h === 0 ? infector : `, ${infector}`
        })
        infectors_string = infectors_string.length === 0 ? "No Data" : infectors_string;
        return infectors_string;
    }

    getCovidGeneralView = () => {
        const { countries_info } = this.state;
        return Object.keys(countries_info).map(country => {
                return (
                    <div key={countries_info[country].uuid} onClick={this.showHiddenData} className="country-info-container">
                        <div className="country-name">
                            {country}   
                        </div>
                        <div className="country-stats-container">
                            <div className="country-stat">casos totales: {this.checkMissingData(countries_info[country].cases)}</div>
                            <div className="country-stat">recuperados: {this.checkMissingData(countries_info[country].total_recoverys)}</div>
                            <div className="country-stat">muertes: {this.checkMissingData(countries_info[country].total_deaths)}</div> 
                            <div className="country-stat">activos: {this.checkMissingData(countries_info[country].cases - (countries_info[country].total_deaths + countries_info[country].total_recoverys))}</div> 
                        </div>
                        <div className="extra-info">
                            <div className="extra-stats">
                                <div className="country-stat extra-stat"> - camas de hospital por cada 1k habitantes: {this.checkMissingData(countries_info[country].hospibed_per_kp)}</div>
                                <div className="country-stat extra-stat"> - test realizados: {this.checkMissingData(countries_info[country].tests_made)}</div>
                                <div className="country-stat extra-stat"> - poblacion:{this.formatBigNumber(countries_info[country].population)}</div> 
                                <div className="country-stat extra-stat"> - lugar del primer brote: {countries_info[country].index_case}</div>
                                <div className="country-stat extra-stat"> - importado desde: {this.formatInfectors(countries_info[country].infectors)}</div>
                            </div>
                            <div className="daily-cases">
                                    <span>Casos por dia</span>
                                    <div className="daily-cases-container">
                                        {countries_info[country].daily_cases.map((dc, k) => {
                                            return (
                                                <div key={`${countries_info[country].uuid}-dc-${k}`} className="daily-case-container">
                                                    <div className="dc-stat dc-date">{dc.date.match(/\d{1,2}\s[A-Za-z]{3}\s\d{4}/g)[0]}</div>
                                                    <div className="dc-stat">casos: {dc.cases}</div>
                                                    <div className="dc-stat">recuperados: {dc.recoverys}</div>
                                                    <div className="dc-stat">muertes:{dc.deaths}</div>
                                                </div>
                                            )
                                        })}                                        
                                    </div>
                            </div>
                        </div>
                    </div>
                )
    })      
}

    render()
    {
        return(
            <React.Fragment>
                <div id="index-main-container" className="page-container">
                    <div id="page-title">COVID-19 Data</div>
                    <div id="data-table">
                        {this.getCovidGeneralView()}
                    </div>
                </div>
            </React.Fragment>
        )
    }
}

export default MainPage;