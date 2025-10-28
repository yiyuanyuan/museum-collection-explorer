import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import Header from './components/Layout/Header';
import MapView from './components/Map/MapView';
import Chatbot from './components/Chatbot/Chatbot';
import { fetchOccurrences } from './services/biocache';

function App() {
  const [occurrences, setOccurrences] = useState([]);
  const [filters, setFilters] = useState({});
  const [facets, setFacets] = useState({});
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [showExplore, setShowExplore] = useState(false);
  const [totalInViewport, setTotalInViewport] = useState(0);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const debounceTimer = useRef(null);

  const loadViewportData = async (bounds, showOnlyWithImages = true) => {
    setLoading(true);
    
    // DEBUG: Log the parameter
    console.log('[App.js DEBUG] loadViewportData called with showOnlyWithImages:', showOnlyWithImages);
    
    try {
      // Use the fetchOccurrences service with proper API URL
      const params = {
        north: bounds.north,
        south: bounds.south,
        east: bounds.east,
        west: bounds.west,
        showOnlyWithImages: showOnlyWithImages,  // Pass the image filter parameter
        ...filters
      };
      
      // DEBUG: Log the params being sent
      console.log('[App.js DEBUG] Calling fetchOccurrences with params:', params);
      
      const data = await fetchOccurrences(params);
      
      // DEBUG: Log the result
      console.log('[App.js DEBUG] Received data:', {
        occurrencesCount: data.occurrences?.length,
        totalRecords: data.totalRecords
      });
      
      setOccurrences(data.occurrences || []);
      setFacets(data.facets || {});
      setTotalInViewport(data.totalRecords || 0);
      
      // After first successful load, set initialLoading to false
      if (initialLoading) {
        setInitialLoading(false);
      }
      
      console.log(`Loaded ${data.occurrences?.length} of ${data.totalRecords} specimens in viewport`);
    } catch (error) {
      console.error('Error loading occurrences:', error);
      // Even on error, remove initial loading after first attempt
      if (initialLoading) {
        setInitialLoading(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
  };

  const handleBoundsChange = (bounds, showOnlyWithImages = true) => {
    // DEBUG: Log bounds change
    console.log('[App.js DEBUG] handleBoundsChange called with showOnlyWithImages:', showOnlyWithImages);
    
    // Debounce the API calls to avoid too many requests
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    
    debounceTimer.current = setTimeout(() => {
      loadViewportData(bounds, showOnlyWithImages);
    }, 500); // Wait 500ms after user stops moving map
  };

  const handleStartExploring = () => {
    setShowExplore(true);
  };

  // Update data when filters change
  useEffect(() => {
    if (showExplore && occurrences.length === 0 && !loading) {
      // Trigger initial load if needed
      const bounds = {
        north: -10,
        south: -45,
        east: 155,
        west: 110
      };
      loadViewportData(bounds);
    }
  }, [showExplore, filters]);

  if (!showExplore) {
    return (
      <div className="app">
        <Header />
        <div className="landing-page">
          <div className="landing-content">
            <div className="museum-label">AUSTRALIAN MUSEUM</div>
            <h1 className="main-title">COLLECTION EXPLORER</h1>
            <div className="landing-nav">
              <span className="nav-item">Digitised Specimen Records on Map</span>
              <span className="nav-divider">•</span>
              <span className="nav-item">AI Chat Assistant</span>
            </div>
            <button className="start-button" onClick={handleStartExploring}>
              START EXPLORING
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <Header />
      <div className="main-content">
        <div className="left-panel">
          <MapView 
            occurrences={occurrences}
            loading={loading}
            initialLoading={initialLoading}
            onBoundsChange={handleBoundsChange}
            totalInViewport={totalInViewport}
            selectedRegion={selectedRegion}
            filters={filters}
            facets={facets}
            onFilterChange={handleFilterChange}
          />
        </div>
        
        <div className="right-panel">
          <Chatbot />
        </div>
      </div>
    </div>
  );
}

export default App;