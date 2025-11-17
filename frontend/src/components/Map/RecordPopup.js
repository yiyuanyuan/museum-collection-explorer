import React, { useState, useEffect, useRef } from 'react';
import posthog from 'posthog-js';

function RecordPopup({ records }) {
  // Handle both single record and array of records
  const recordsArray = Array.isArray(records) ? records : [records];
  
  const [currentIndex, setCurrentIndex] = useState(0);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
  const [slideDirection, setSlideDirection] = useState('right'); // 'left' or 'right'
  const [hasTransitioned, setHasTransitioned] = useState(false); // Track if we've transitioned at least once
  const autoScrollTimerRef = useRef(null);
  const recordViewStartTimeRef = useRef(Date.now());
  
  const currentRecord = recordsArray[currentIndex];
  const totalRecords = recordsArray.length;
  const hasMultipleRecords = totalRecords > 1;
  
  // Track when individual record is viewed
  useEffect(() => {
    if (currentRecord) {
      recordViewStartTimeRef.current = Date.now();
      
      posthog.capture('popup_record_viewed', {
        scientific_name: currentRecord.scientificName,
        common_name: currentRecord.commonName,
        catalogue_number: currentRecord.catalogueNumber,
        institution: currentRecord.institutionName,
        collection: currentRecord.collectionName,
        state: currentRecord.stateProvince,
        locality: currentRecord.locality,
        has_image: !!(currentRecord.thumbnailUrl || currentRecord.imageUrl || currentRecord.largeImageUrl),
        event_date: currentRecord.eventDate,
        recorded_by: currentRecord.recordedBy,
        location: {
          lat: currentRecord.latitude,
          lng: currentRecord.longitude
        },
        record_position: currentIndex + 1,
        total_records_at_location: totalRecords,
        navigation_method: autoScrollEnabled ? 'auto_scroll' : 'manual',
        timestamp: new Date().toISOString()
      });
    }
  }, [currentIndex, currentRecord, totalRecords, autoScrollEnabled]);
  
  // Auto-scroll functionality
  useEffect(() => {
    if (autoScrollEnabled && hasMultipleRecords) {
      autoScrollTimerRef.current = setInterval(() => {
        setSlideDirection('right'); // Auto-scroll always goes right
        setHasTransitioned(true); // Mark that we've started transitioning
        setCurrentIndex((prevIndex) => (prevIndex + 1) % totalRecords);
      }, 3000); // Auto-scroll every 3 seconds
      
      return () => {
        if (autoScrollTimerRef.current) {
          clearInterval(autoScrollTimerRef.current);
        }
      };
    }
  }, [autoScrollEnabled, hasMultipleRecords, totalRecords]);
  
  // Reset to first record and restart auto-scroll when records change (new location)
  useEffect(() => {
    setCurrentIndex(0);
    setAutoScrollEnabled(true);
    setSlideDirection('right');
    setHasTransitioned(false); // Reset transition flag for new location
    recordViewStartTimeRef.current = Date.now();
  }, [recordsArray]);
  
  const goToNext = () => {
    // Calculate time spent viewing current record
    const timeViewing = (Date.now() - recordViewStartTimeRef.current) / 1000;
    
    // Track navigation
    posthog.capture('popup_carousel_navigated', {
      direction: 'next',
      from_index: currentIndex,
      to_index: (currentIndex + 1) % totalRecords,
      total_records: totalRecords,
      time_viewing_previous_record_seconds: timeViewing,
      current_record: {
        scientific_name: currentRecord.scientificName,
        catalogue_number: currentRecord.catalogueNumber
      },
      navigation_method: 'manual_button',
      timestamp: new Date().toISOString()
    });
    
    setAutoScrollEnabled(false); // Stop auto-scroll on user interaction
    setSlideDirection('right');
    setHasTransitioned(true);
    setCurrentIndex((prevIndex) => (prevIndex + 1) % totalRecords);
  };
  
  const goToPrevious = () => {
    // Calculate time spent viewing current record
    const timeViewing = (Date.now() - recordViewStartTimeRef.current) / 1000;
    
    // Track navigation
    posthog.capture('popup_carousel_navigated', {
      direction: 'previous',
      from_index: currentIndex,
      to_index: (currentIndex - 1 + totalRecords) % totalRecords,
      total_records: totalRecords,
      time_viewing_previous_record_seconds: timeViewing,
      current_record: {
        scientific_name: currentRecord.scientificName,
        catalogue_number: currentRecord.catalogueNumber
      },
      navigation_method: 'manual_button',
      timestamp: new Date().toISOString()
    });
    
    setAutoScrollEnabled(false); // Stop auto-scroll on user interaction
    setSlideDirection('left');
    setHasTransitioned(true);
    setCurrentIndex((prevIndex) => (prevIndex - 1 + totalRecords) % totalRecords);
  };
  
  const handleClose = () => {
    // Calculate time spent viewing current record
    const timeViewing = (Date.now() - recordViewStartTimeRef.current) / 1000;
    
    // Track popup close button click
    posthog.capture('popup_close_button_clicked', {
      current_record_index: currentIndex,
      total_records: totalRecords,
      time_viewing_last_record_seconds: timeViewing,
      current_record: {
        scientific_name: currentRecord.scientificName,
        catalogue_number: currentRecord.catalogueNumber
      },
      timestamp: new Date().toISOString()
    });
    
    // Close the popup by finding and clicking the leaflet close button
    const closeButton = document.querySelector('.leaflet-popup-close-button');
    if (closeButton) {
      closeButton.click();
    }
  };
  
  if (!currentRecord) return null;
  
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
  
  const displayImage = currentRecord.thumbnailUrl || currentRecord.imageUrl || currentRecord.largeImageUrl;
  
  // Determine if we should animate
  const shouldAnimate = hasMultipleRecords && hasTransitioned;
  
  return (
    <div className="record-popup">
      {/* Close button */}
      <button className="popup-close-btn" onClick={handleClose} title="Close">
        ✕
      </button>
      
      {/* Animated content wrapper - only animate if multiple records AND not first record */}
      <div 
        className={shouldAnimate ? "popup-content-wrapper" : "popup-content-wrapper-static"}
        key={shouldAnimate ? currentIndex : 'initial'}
        data-slide-direction={shouldAnimate ? slideDirection : undefined}
      >
        {displayImage && (
          <div className="popup-image">
            <img 
              src={displayImage} 
              alt={currentRecord.scientificName || 'Specimen'}
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          </div>
        )}
        
        <div className="popup-content">
          {currentRecord.commonName && (
            <h4 className="common-name">{currentRecord.commonName}</h4>
          )}
          
          <p className="scientific-name">
            <em>{currentRecord.scientificName || 'Unknown species'}</em>
          </p>
          
          <div className="popup-details">
            {currentRecord.catalogNumber && (
              <div className="detail-row">
                <span className="detail-label">Catalog:</span>
                <span className="detail-value">{currentRecord.catalogNumber}</span>
              </div>
            )}
            
            {currentRecord.institutionName && (
              <div className="detail-row">
                <span className="detail-label">Institution:</span>
                <span className="detail-value">{currentRecord.institutionName}</span>
              </div>
            )}
            
            {currentRecord.collectionName && (
              <div className="detail-row">
                <span className="detail-label">Collection:</span>
                <span className="detail-value">{currentRecord.collectionName}</span>
              </div>
            )}
            
            {currentRecord.recordedBy && (
              <div className="detail-row">
                <span className="detail-label">Recorded By:</span>
                <span className="detail-value">{currentRecord.recordedBy}</span>
              </div>
            )}
            
            {currentRecord.eventDate && (
              <div className="detail-row">
                <span className="detail-label">Date:</span>
                <span className="detail-value">{formatDate(currentRecord.eventDate)}</span>
              </div>
            )}
            
            {currentRecord.locality && (
              <div className="detail-row">
                <span className="detail-label">Locality:</span>
                <span className="detail-value">{currentRecord.locality}</span>
              </div>
            )}
            
            {currentRecord.stateProvince && (
              <div className="detail-row">
                <span className="detail-label">State:</span>
                <span className="detail-value">{currentRecord.stateProvince}</span>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Navigation controls - only show if multiple records */}
      {hasMultipleRecords && (
        <div className="popup-navigation">
          <button 
            className="nav-btn nav-btn-left" 
            onClick={goToPrevious}
            title="Previous record"
          >
            ◄
          </button>
          <span className="record-counter">
            {currentIndex + 1} of {totalRecords}
          </span>
          <button 
            className="nav-btn nav-btn-right" 
            onClick={goToNext}
            title="Next record"
          >
            ►
          </button>
        </div>
      )}
      
      <style jsx>{`
        .record-popup {
          min-width: 250px;
          position: relative;
          overflow: hidden;
        }
        
        .popup-close-btn {
          position: absolute;
          top: 4px;
          right: 4px;
          width: 24px;
          height: 24px;
          border: none;
          background: rgba(0, 0, 0, 0.6);
          color: white;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          z-index: 1000;
          transition: background 0.2s;
        }
        
        .popup-close-btn:hover {
          background: rgba(0, 0, 0, 0.8);
        }
        
        /* Animated wrapper for multiple records */
        .popup-content-wrapper {
          animation-duration: 0.5s;
          animation-timing-function: ease-in-out;
          animation-fill-mode: both;
        }
        
        .popup-content-wrapper[data-slide-direction="right"] {
          animation-name: slideInFromRight;
        }
        
        .popup-content-wrapper[data-slide-direction="left"] {
          animation-name: slideInFromLeft;
        }
        
        /* Static wrapper for single records or first record - no animation */
        .popup-content-wrapper-static {
          /* No animation */
        }
        
        @keyframes slideInFromRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        
        @keyframes slideInFromLeft {
          from {
            transform: translateX(-100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        
        .popup-image {
          margin: -8px -8px 8px -8px;
          overflow: hidden;
          border-radius: 4px 4px 0 0;
          position: relative;
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
          margin-bottom: 0.75rem;
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
        
        .popup-navigation {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 1rem;
          padding: 0.5rem 0;
          border-top: 1px solid #e0e0e0;
          margin-top: 0.5rem;
        }
        
        .nav-btn {
          width: 32px;
          height: 32px;
          border: 1px solid #d0d0d0;
          background: white;
          color: #333;
          border-radius: 4px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          transition: all 0.2s;
        }
        
        .nav-btn:hover {
          background: #f5f5f5;
          border-color: #999;
        }
        
        .nav-btn:active {
          background: #e0e0e0;
        }
        
        .record-counter {
          font-size: 0.75rem;
          color: #666;
          font-weight: 500;
          min-width: 60px;
          text-align: center;
        }
      `}</style>
    </div>
  );
}

export default RecordPopup;