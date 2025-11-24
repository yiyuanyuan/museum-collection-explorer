import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './MapView.css';
import RecordPopup from './RecordPopup';
import FilterPanel from '../Filters/FilterPanel';
import posthog from 'posthog-js';

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
  const previousZoomRef = useRef(null);
  
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
        
        // Track map pan
        const center = map.getCenter();
        posthog.capture('map_panned', {
          center: {
            lat: center.lat,
            lng: center.lng
          },
          bounds: {
            north: bounds.north,
            south: bounds.south,
            east: bounds.east,
            west: bounds.west
          },
          zoom_level: map.getZoom(),
          timestamp: new Date().toISOString()
        });
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
      previousZoomRef.current = map.getZoom();
    },
    zoomend: () => {
      const currentZoom = map.getZoom();
      const previousZoom = previousZoomRef.current;
      
      if (!isPopupOpen || userInteractionRef.current) {
        const bounds = getVisibleBounds();
        onBoundsChange(bounds);
        
        // Track map zoom
        const center = map.getCenter();
        posthog.capture('map_zoomed', {
          zoom_level: currentZoom,
          previous_zoom: previousZoom,
          zoom_direction: currentZoom > previousZoom ? 'in' : 'out',
          zoom_delta: currentZoom - previousZoom,
          center: {
            lat: center.lat,
            lng: center.lng
          },
          bounds: {
            north: bounds.north,
            south: bounds.south,
            east: bounds.east,
            west: bounds.west
          },
          timestamp: new Date().toISOString()
        });
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
        
        // Track initial map load
        const center = map.getCenter();
        posthog.capture('map_loaded', {
          initial_center: {
            lat: center.lat,
            lng: center.lng
          },
          initial_zoom: map.getZoom(),
          initial_bounds: {
            north: bounds.north,
            south: bounds.south,
            east: bounds.east,
            west: bounds.west
          },
          timestamp: new Date().toISOString()
        });
      }, 100);
    }
  }, [hasInitialized, map, onBoundsChange]);
  
  useEffect(() => {
    if (selectedRegion && map) {
      map.flyTo(selectedRegion.coordinates, selectedRegion.zoom, {
        duration: 1.5,
        easeLinearity: 0.5
      });
      
      // Track region selection
      posthog.capture('map_region_selected', {
        region: selectedRegion.name || 'unknown',
        target_coordinates: selectedRegion.coordinates,
        target_zoom: selectedRegion.zoom,
        timestamp: new Date().toISOString()
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
  const popupOpenTimeRef = useRef(null);
  
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
      }
    }
  }, [groupedOccurrences]);
  
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    
    if (isPopupOpen) {
      map.dragging.disable();
      map.scrollWheelZoom.disable();
    } else {
      map.dragging.enable();
      map.scrollWheelZoom.enable();
    }
    
    if (map) {
      const handlePopupOpen = (e) => {
        const { lat, lng } = e.popup._latlng;
        const markerKey = `${lat.toFixed(6)},${lng.toFixed(6)}`;
        const group = groupedOccurrences.find(g => g.key === markerKey);
        
        if (group) {
          openPopupInfo.current = {
            lat: lat.toFixed(6),
            lng: lng.toFixed(6),
            recordIds: group.records.map(r => r.id)
          };
          setIsPopupOpen(true);
          popupOpenTimeRef.current = Date.now();
          
          // Track popup opened
          const currentZoom = map.getZoom();
          const center = map.getCenter();
          
          posthog.capture('map_popup_opened', {
            location: {
              lat: parseFloat(lat),
              lng: parseFloat(lng)
            },
            record_count: group.records.length,
            records: group.records.map(record => ({
              scientific_name: record.scientificName,
              common_name: record.commonName,
              catalogue_number: record.catalogueNumber,
              institution: record.institutionName,
              collection: record.collectionName,
              state: record.stateProvince,
              locality: record.locality,
              has_image: !!(record.thumbnailUrl || record.imageUrl || record.largeImageUrl),
              event_date: record.eventDate,
              recorded_by: record.recordedBy
            })),
            map_state: {
              zoom_level: currentZoom,
              center: {
                lat: center.lat,
                lng: center.lng
              }
            },
            timestamp: new Date().toISOString()
          });
        }
        
        isAutoPanning.current = true;
        setTimeout(() => {
          isAutoPanning.current = false;
        }, 600);
      };
      
      const handlePopupClose = () => {
        // Calculate time popup was open
        const timeOpen = popupOpenTimeRef.current 
          ? (Date.now() - popupOpenTimeRef.current) / 1000 
          : 0;
        
        if (openPopupInfo.current) {
          const { lat, lng } = openPopupInfo.current;
          const group = groupedOccurrences.find(g => g.key === `${lat},${lng}`);
          
          if (group) {
            // Track popup closed
            posthog.capture('map_popup_closed', {
              location: {
                lat: parseFloat(lat),
                lng: parseFloat(lng)
              },
              record_count: group.records.length,
              time_open_seconds: timeOpen,
              timestamp: new Date().toISOString()
            });
          }
        }
        
        setIsPopupOpen(false);
        openPopupInfo.current = null;
        reopenAttempted.current = false;
        isAutoPanning.current = false;
        popupOpenTimeRef.current = null;
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
    
    // Track image filter toggle
    posthog.capture('map_image_filter_toggled', {
      filter_enabled: newValue,
      timestamp: new Date().toISOString()
    });
    
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
    const newValue = !isFullscreen;
    setIsFullscreen(newValue);
    
    // Track fullscreen toggle
    posthog.capture('map_fullscreen_toggled', {
      fullscreen_enabled: newValue,
      timestamp: new Date().toISOString()
    });
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
                eventHandlers={{
                  click: () => {
                    // Track marker click
                    posthog.capture('map_marker_clicked', {
                      location: {
                        lat: group.latitude,
                        lng: group.longitude
                      },
                      record_count: group.records.length,
                      has_multiple_records: group.records.length > 1,
                      timestamp: new Date().toISOString()
                    });
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
        <div className="footer-row">
          <div className="data-source">
            <span className="source-label">Data Source:</span>
            <span className="source-name">Atlas of Living Australia</span>
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
        <div className="footer-note">
          <p className="note-text">
            Note: This prototype displays only a portion of the Australian Museum's digitised specimen collections, and information on some records might be incomplete.
          </p>
        </div>
      </div>
    </div>
  );
}

export default MapView;