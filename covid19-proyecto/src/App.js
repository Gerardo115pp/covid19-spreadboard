import React from 'react';
import { Router, Switch, Route } from 'react-router-dom';
import MainPage from './pages/Index';
import historial from './historial';

function App() {
  return (
    <div className="App">
      <Router history={historial}>
        <Switch>
          <Route exact component={MainPage} path='/'/>
        </Switch>
      </Router>
    </div>
  );
}

export default App;
