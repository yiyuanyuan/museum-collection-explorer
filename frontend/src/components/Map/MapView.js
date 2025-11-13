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
    const fixMapSize = () => {
      map.invalidateSize(true);
      const center = map.getCenter();
      map.setView(center, map.getZoom(), { animate: false });
    };
    
    const timer = setTimeout(fixMapSize, 350);
    
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
function ViewportManager({ onBoundsChange, selectedRegion, isPopupOpen, isAutoPanning, onUserInteraction }) {
  const map = useMap();
  const [hasInitialized, setHasInitialized] = useState(false);
  const userInteractionRef = useRef(false);
  
  const getVisibleBounds = () => {
    const container = map.getContainer();
    const containerBounds = container.getBoundingClientRect();
    
    const topLeft = map.containerPointToLatLng([0, 0]);
    const bottomRight = map.containerPointToLatLng([containerBounds.width, containerBounds.height]);
    
    return {
      north: topLeft.lat,
      south: bottomRight.lat,
      east: bottomRight.lng,
      west: topLeft.lng
    };
  };
  
  useMapEvents({
    movestart: () => {
      if (isPopupOpen && !isAutoPanning.current) {
        userInteractionRef.current = true;
        if (onUserInteraction) {
          onUserInteraction();
        }
      }
    },
    moveend: () => {
      if (!isPopupOpen || userInteractionRef.current) {
        const bounds = getVisibleBounds();
        onBoundsChange(bounds);
      }
      userInteractionRef.current = false;
    },
    zoomstart: () => {
      if (isPopupOpen) {
        userInteractionRef.current = true;
        if (onUserInteraction) {
          onUserInteraction();
        }
      }
    },
    zoomend: () => {
      if (!isPopupOpen || userInteractionRef.current) {
        const bounds = getVisibleBounds();
        onBoundsChange(bounds);
      }
      userInteractionRef.current = false;
    }
  });
  
  useEffect(() => {
    if (!hasInitialized && map) {
      setTimeout(() => {
        const bounds = getVisibleBounds();
        onBoundsChange(bounds);
        setHasInitialized(true);
      }, 100);
    }
  }, [hasInitialized, map, onBoundsChange]);
  
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
  const [mapCenter] = useState([-25.2744, 133.7751]);
  const [mapZoom] = useState(4);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [showOnlyWithImages, setShowOnlyWithImages] = useState(true);
  const openPopupInfo = useRef(null);
  const isAutoPanning = useRef(false);
  const mapRef = useRef(null);
  const markerRefs = useRef({});
  const reopenAttempted = useRef(false);
  
  // Group occurrences by location (same lat/lng)
  const groupedOccurrences = React.useMemo(() => {
    const groups = {};
    
    occurrences.forEach((record) => {
      const lat = record.latitude.toFixed(6);
      const lng = record.longitude.toFixed(6);
      const key = `${lat},${lng}`;
      
      if (!groups[key]) {
        groups[key] = {
          latitude: record.latitude,
          longitude: record.longitude,
          records: [],
          key: key
        };
      }
      
      groups[key].records.push(record);
    });
    
    return Object.values(groups);
  }, [occurrences]);
  
  useEffect(() => {
    if (openPopupInfo.current && !reopenAttempted.current) {
      reopenAttempted.current = true;
      
      const { lat, lng, recordIds } = openPopupInfo.current;
      const key = `${lat},${lng}`;
      
      const matchingGroup = groupedOccurrences.find(group => group.key === key);
      
      if (matchingGroup && markerRefs.current[key]) {
        const hasMatchingRecord = matchingGroup.records.some(record => 
          recordIds.includes(record.id)
        );
        
        if (hasMatchingRecord) {
          const marker = markerRefs.current[key];
          if (marker && marker.openPopup) {
            setTimeout(() => {
              marker.openPopup();
              reopenAttempted.current = false;
            }, 100);
          }
        } else {
          openPopupInfo.current = null;
          reopenAttempted.current = false;
        }
      } else {
        openPopupInfo.current = null;
        reopenAttempted.current = false;
      }
    }
  }, [groupedOccurrences]);
  
  useEffect(() => {
    if (mapRef.current) {
      const map = mapRef.current;
      
      const handlePopupOpen = (e) => {
        setIsPopupOpen(true);
        
        const latlng = e.popup._latlng;
        const lat = latlng.lat.toFixed(6);
        const lng = latlng.lng.toFixed(6);
        const key = `${lat},${lng}`;
        
        const group = groupedOccurrences.find(g => g.key === key);
        if (group) {
          openPopupInfo.current = {
            lat: lat,
            lng: lng,
            recordIds: group.records.map(r => r.id)
          };
        }
        
        isAutoPanning.current = true;
        setTimeout(() => {
          isAutoPanning.current = false;
        }, 600);
      };
      
      const handlePopupClose = () => {
        setIsPopupOpen(false);
        openPopupInfo.current = null;
        reopenAttempted.current = false;
        isAutoPanning.current = false;
      };
      
      map.on('popupopen', handlePopupOpen);
      map.on('popupclose', handlePopupClose);
      
      return () => {
        map.off('popupopen', handlePopupOpen);
        map.off('popupclose', handlePopupClose);
      };
    }
  }, [groupedOccurrences]);

  const handleUserInteraction = () => {
    if (mapRef.current) {
      mapRef.current.closePopup();
    }
    openPopupInfo.current = null;
    setIsPopupOpen(false);
  };
  
  const handleBoundsChangeWithFilter = (bounds) => {
    onBoundsChange(bounds, showOnlyWithImages);
  };

  const toggleImageFilter = () => {
    const newValue = !showOnlyWithImages;
    setShowOnlyWithImages(newValue);
    if (mapRef.current) {
      const map = mapRef.current;
      const bounds = map.getBounds();
      onBoundsChange({
        north: bounds.getNorth(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        west: bounds.getWest()
      }, newValue);
    }
  };
  
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };
  
  return (
    <div className={`map-view-container ${isFullscreen ? 'fullscreen' : ''}`}>
      <div className="map-header">
        <div className="header-content">
          <h3 className="map-title">Specimen Map</h3>
          <p className="map-subtitle">
            Zoom in and click on markers to view specimens
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
      
      <div className="map-content">
        <MapContainer 
          center={mapCenter} 
          zoom={mapZoom} 
          className="leaflet-map"
          zoomControl={true}
          ref={mapRef}
          whenReady={(mapInstance) => {
            mapRef.current = mapInstance.target;
          }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          />
          
          <FullscreenHandler isFullscreen={isFullscreen} />
          
          <ViewportManager 
            onBoundsChange={handleBoundsChangeWithFilter} 
            selectedRegion={selectedRegion}
            isPopupOpen={isPopupOpen}
            isAutoPanning={isAutoPanning}
            onUserInteraction={handleUserInteraction}
          />
          
          {groupedOccurrences.map((group) => {
            const markerKey = group.key;
            return (
              <Marker
                key={`${markerKey}-${group.records.length}-${group.records[0].id}`}
                position={[group.latitude, group.longitude]}
                ref={(ref) => {
                  if (ref) {
                    markerRefs.current[markerKey] = ref;
                  }
                }}
              >
                <Popup maxWidth={300} minWidth={250}>
                  <RecordPopup records={group.records} />
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
        
        {/* iOS-style toggle switch - positioned below zoom controls */}
        <div className="image-filter-toggle">
          <label className="toggle-switch">
            <input 
              type="checkbox" 
              checked={showOnlyWithImages}
              onChange={toggleImageFilter}
            />
            <span className="toggle-slider"></span>
          </label>
          <span className="toggle-label">
            {showOnlyWithImages ? 'Show Only Records with Images' : 'Show Only Records with Images'}
          </span>
        </div>
        
        {initialLoading && loading && (
          <div className="loading-overlay">
            <div className="loading-spinner"></div>
            <p>Loading specimens...</p>
          </div>
        )}
        
        {!initialLoading && loading && (
          <div className="loading-indicator">
            <div className="loading-spinner"></div>
          </div>
        )}
      </div>
      
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