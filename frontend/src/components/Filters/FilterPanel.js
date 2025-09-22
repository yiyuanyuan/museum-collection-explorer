import React from 'react';
import './FilterPanel.css';

function FilterPanel({ facets, onFilterChange, currentFilters }) {
  const handleFilterChange = (filterType, value) => {
    const newFilters = { ...currentFilters };
    
    if (value === '') {
      delete newFilters[filterType];
    } else {
      newFilters[filterType] = value;
    }
    
    onFilterChange(newFilters);
  };

  return (
    <div className="filter-panel">
      <div className="filter-group">
        <label>Collection Name</label>
        <select 
          onChange={(e) => handleFilterChange('collectionName', e.target.value)}
          value={currentFilters.collectionName || ''}
        >
          <option value="">All Collections</option>
          {facets.collection_name?.map(item => (
            <option key={item.value} value={item.value}>
              {item.value} ({item.count})
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label>State/Province</label>
        <select 
          onChange={(e) => handleFilterChange('stateProvince', e.target.value)}
          value={currentFilters.stateProvince || ''}
        >
          <option value="">All States</option>
          {facets.state_province?.map(item => (
            <option key={item.value} value={item.value}>
              {item.value} ({item.count})
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label>Year</label>
        <select 
          onChange={(e) => handleFilterChange('year', e.target.value)}
          value={currentFilters.year || ''}
        >
          <option value="">All Years</option>
          {facets.year?.map(item => (
            <option key={item.value} value={item.value}>
              {item.value} ({item.count})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

export default FilterPanel;