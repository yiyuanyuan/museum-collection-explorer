import React from 'react';

function RecordPopup({ record }) {
  if (!record) return null;

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-AU', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  // Use thumbnailUrl first, then imageUrl, then largeImageUrl
  const displayImage = record.thumbnailUrl || record.imageUrl || record.largeImageUrl;

  return (
    <div className="record-popup">
      {displayImage && (
        <div className="popup-image">
          <img 
            src={displayImage} 
            alt={record.scientificName || 'Specimen'}
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        </div>
      )}
      
      <div className="popup-content">
        {record.commonName && (
          <h4 className="common-name">{record.commonName}</h4>
        )}
        
        <p className="scientific-name">
          <em>{record.scientificName || 'Unknown species'}</em>
        </p>
        
        <div className="popup-details">
          {record.catalogNumber && (
            <div className="detail-row">
              <span className="detail-label">Catalog:</span>
              <span className="detail-value">{record.catalogNumber}</span>
            </div>
          )}
          
          {record.institutionName && (
            <div className="detail-row">
              <span className="detail-label">Institution:</span>
              <span className="detail-value">{record.institutionName}</span>
            </div>
          )}
          
          {record.collectionName && (
            <div className="detail-row">
              <span className="detail-label">Collection:</span>
              <span className="detail-value">{record.collectionName}</span>
            </div>
          )}
          
          {record.basisOfRecord && (
            <div className="detail-row">
              <span className="detail-label">Recorded By:</span>
              <span className="detail-value">{record.recordedBy}</span>
            </div>
          )}
          
          {record.eventDate && (
            <div className="detail-row">
              <span className="detail-label">Date:</span>
              <span className="detail-value">{formatDate(record.eventDate)}</span>
            </div>
          )}
          
          {record.locality && (
            <div className="detail-row">
              <span className="detail-label">Locality:</span>
              <span className="detail-value">{record.locality}</span>
            </div>
          )}
          
          {record.stateProvince && (
            <div className="detail-row">
              <span className="detail-label">State:</span>
              <span className="detail-value">{record.stateProvince}</span>
            </div>
          )}
        </div>
      </div>
      
      <style jsx>{`
        .record-popup {
          min-width: 250px;
        }
        
        .popup-image {
          margin: -8px -8px 8px -8px;
          overflow: hidden;
          border-radius: 4px 4px 0 0;
        }
        
        .popup-image img {
          width: 100%;
          height: 150px;
          object-fit: cover;
        }
        
        .popup-content {
          padding: 0.5rem 0;
        }
        
        .common-name {
          font-size: 1rem;
          font-weight: 600;
          color: #333;
          margin: 0 0 0.25rem 0;
        }
        
        .scientific-name {
          font-size: 0.875rem;
          color: #666;
          margin: 0 0 0.75rem 0;
        }
        
        .popup-details {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        
        .detail-row {
          display: flex;
          font-size: 0.8125rem;
        }
        
        .detail-label {
          font-weight: 500;
          color: #666;
          min-width: 70px;
          margin-right: 0.5rem;
        }
        
        .detail-value {
          color: #333;
          flex: 1;
        }
      `}</style>
    </div>
  );
}

export default RecordPopup;