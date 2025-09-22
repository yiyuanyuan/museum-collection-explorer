import React from 'react';
import './Statistics.css';

function Statistics({ statistics, onRegionClick }) {
  // Default statistics matching the screenshot
  const defaultStats = {
    totalSpecimens: 59295,
    byRegion: {
      'New South Wales': 37157,
      'Queensland': 8083,
      'Western Australia': 2613,
      'Northern Territory': 1949,
      'Tasmania': 1896,
      'South Australia': 1216,
      'Victoria': 1206
    }
  };

  const stats = statistics || defaultStats;

  // Region coordinates for map navigation
  const regionCoordinates = {
    'New South Wales': [-32.1, 147.0],
    'Victoria': [-36.5, 144.0],
    'Queensland': [-22.0, 144.0],
    'Western Australia': [-25.0, 122.0],
    'South Australia': [-30.0, 135.0],
    'Tasmania': [-42.0, 147.0],
    'Northern Territory': [-19.0, 133.0],
  };

  const handleRegionClick = (regionName) => {
    const coordinates = regionCoordinates[regionName];
    if (coordinates && onRegionClick) {
      onRegionClick({
        name: regionName,
        coordinates: coordinates,
        zoom: 6
      });
    }
  };

  return (
    <div className="statistics-container">
      <div className="statistics-header">
        <h3>COLLECTION STATISTICS</h3>
        <div className="total-specimens">
          TOTAL SPECIMENS: <strong>{stats.totalSpecimens.toLocaleString()}</strong>
        </div>
      </div>
      
      <div className="statistics-content">
        <div className="region-label">BY REGION</div>
        <div className="region-stats">
          {Object.entries(stats.byRegion).map(([region, count]) => (
            <div 
              key={region} 
              className="stat-item"
              onClick={() => handleRegionClick(region)}
              title={`Click to view ${region} on map`}
            >
              <span className="region-name">{region}</span>
              <span className="specimen-count">{count.toLocaleString()} specimens</span>
            </div>
          ))}
        </div>
      </div>

      <div className="map-attribution">
        <a href="https://leafletjs.com" target="_blank" rel="noopener noreferrer">
          Leaflet
        </a>
        {' | © '}
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">
          OpenStreetMap
        </a>
        {' contributors'}
      </div>
    </div>
  );
}

export default Statistics;