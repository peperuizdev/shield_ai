import React from 'react';
import Header from './components/Layout/Header';
import MainContainer from './components/Layout/MainContainer';
import Footer from './components/Layout/Footer';
import { AppProvider } from './contexts/AppContext';
import ErrorBoundary from './components/Common/ErrorBoundary';
import './App.css';

function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <div className="App min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
          <Header />
          <MainContainer />
          <Footer />
        </div>
      </AppProvider>
    </ErrorBoundary>
  );
}

export default App;