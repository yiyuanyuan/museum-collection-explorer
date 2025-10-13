import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './MapView.css';
import RecordPopup from './RecordPopup';
import FilterPanel from '../Filters/FilterPanel';

// Fix for default markers in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Component to handle fullscreen resize
function FullscreenHandler({ isFullscreen }) {
  const map = useMap();
  
  useEffect(() => {
    // Function to fix map size
    const fixMapSize = () => {
      map.invalidateSize(true); // true forces update even if size appears unchanged
      // Force a pan to trigger tile loading
      const center = map.getCenter();
      map.setView(center, map.getZoom(), { animate: false });
    };
    
    // When fullscreen changes, fix size after transitions
    const timer = setTimeout(fixMapSize, 350);
    
    // Also listen for window resize events
    const handleResize = () => {
      setTimeout(fixMapSize, 100);
    };
    
    window.addEventListener('resize', handleResize);
    
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', handleResize);
    };
  }, [isFullscreen, map]);
  
  return null;
}

// Component to handle map events
function ViewportManager({ onBoundsChange, selectedRegion }) {
  const map = useMap();
  const [hasInitialized, setHasInitialized] = useState(false);
  
  const getVisibleBounds = () => {
    // Get the actual map container size
    const container = map.getContainer();
    const containerBounds = container.getBoundingClientRect();
    
    // Get the pixel bounds of the visible area
    const topLeft = map.containerPointToLatLng([0, 0]);
    const bottomRight = map.containerPointToLatLng([containerBounds.width, containerBounds.height]);
    
    // Return the actual visible bounds
    return {
      north: topLeft.lat,
      south: bottomRight.lat,
      east: bottomRight.lng,
      west: topLeft.lng
    };
  };
  
  useMapEvents({
    moveend: () => {
      const bounds = getVisibleBounds();
      onBoundsChange(bounds);
    },
    zoomend: () => {
      const bounds = getVisibleBounds();
      onBoundsChange(bounds);
    }
  });
  
  // Initial load
  useEffect(() => {
    if (!hasInitialized && map) {
      // Wait for map to be fully loaded
      setTimeout(() => {
        const bounds = getVisibleBounds();
        onBoundsChange(bounds);
        setHasInitialized(true);
      }, 100);
    }
  }, [hasInitialized, map, onBoundsChange]);
  
  // Handle region selection
  useEffect(() => {
    if (selectedRegion && map) {
      map.flyTo(selectedRegion.coordinates, selectedRegion.zoom, {
        duration: 1.5,
        easeLinearity: 0.5
      });
    }
  }, [selectedRegion, map]);
  
  return null;
}

function MapView({ 
  occurrences, 
  loading, 
  initialLoading,
  onBoundsChange, 
  totalInViewport, 
  selectedRegion,
  filters,
  facets,
  onFilterChange 
}) {
  const [mapCenter] = useState([-25.2744, 133.7751]); // Center of Australia
  const [mapZoom] = useState(4);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };
  
  return (
    <div className={`map-view-container ${isFullscreen ? 'fullscreen' : ''}`}>
      <div className="map-header">
        <div className="header-content">
          <h3 className="map-title">Specimen Collection Map</h3>
          <p className="map-subtitle">
            Keep zooming in and click on markers to explore specimens
          </p>
        </div>
        <button 
          onClick={toggleFullscreen} 
          className="fullscreen-btn"
          title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
        >
          {isFullscreen ? '⤓' : '⤢'}
        </button>
      </div>
      {/*
      <div className="map-filters">
        <FilterPanel 
          facets={facets}
          onFilterChange={onFilterChange}
          currentFilters={filters}
        />
      </div>
      */}
      <div className="map-content">
        <MapContainer 
          center={mapCenter} 
          zoom={mapZoom} 
          className="leaflet-map"
          zoomControl={true}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          
          <FullscreenHandler isFullscreen={isFullscreen} />
          
          <ViewportManager 
            onBoundsChange={onBoundsChange} 
            selectedRegion={selectedRegion}
          />
          
          {/* Individual markers - NO CLUSTERING */}
          {occurrences.map((record) => (
            <Marker
              key={record.id}
              position={[record.latitude, record.longitude]}
            >
              <Popup>
                <RecordPopup record={record} />
              </Popup>
            </Marker>
          ))}
        </MapContainer>
        
        {/* Initial loading overlay - only for first load */}
        {initialLoading && loading && (
          <div className="loading-overlay">
            <div className="loading-spinner"></div>
            <p>Loading specimens...</p>
          </div>
        )}
        
        {/* Regular loading indicator - for subsequent loads */}
        {!initialLoading && loading && (
          <div className="loading-indicator">
            <div className="loading-spinner"></div>
          </div>
        )}
      </div>
      
      {/* Data info footer */}
      <div className="map-footer">
        <div className="data-source">
          <span className="source-label">Data Source:</span>
          <span className="source-name">ALA Biocache</span>
        </div>
        <div className="data-stats">
          {loading ? (
            <span className="stats-loading">Updating...</span>
          ) : occurrences.length > 0 ? (
            <>
              <span className="stats-showing">
                Showing <strong>{occurrences.length.toLocaleString()}</strong>
              </span>
              {totalInViewport > occurrences.length && (
                <span className="stats-total">
                  of <strong>{totalInViewport.toLocaleString()}</strong> specimens
                </span>
              )}
              {totalInViewport > 2000 && (
                <span className="stats-limit">(API limit: 5000)</span>
              )}
            </>
          ) : (
            <span className="stats-empty">No specimens in current view</span>
          )}
        </div>
      </div>
    </div>
  );
}

export default MapView;