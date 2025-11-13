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
  const [hasConsented, setHasConsented] = useState(false);
  const [shakeConsent, setShakeConsent] = useState(false);
  const [isChatbotExpanded, setIsChatbotExpanded] = useState(false);
  const [isSurveyExpanded, setIsSurveyExpanded] = useState(false);
  const [drawerDragOffset, setDrawerDragOffset] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const debounceTimer = useRef(null);
  const touchStartY = useRef(null);
  const touchStartTime = useRef(null);
  const drawerRef = useRef(null);

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
    if (!hasConsented) {
      // Trigger shake animation
      setShakeConsent(true);
      setTimeout(() => setShakeConsent(false), 500);
      return;
    }
    setShowExplore(true);
  };

  const handleConsentChange = (e) => {
    setHasConsented(e.target.checked);
  };

  const handleNavigateToExplore = () => {
    if (!hasConsented) {
      // Trigger shake animation
      setShakeConsent(true);
      setTimeout(() => setShakeConsent(false), 500);
      return false;
    }
    setShowExplore(true);
    return true;
  };

  const handleNavigateToHome = () => {
    setShowExplore(false);
  };

  const toggleChatbot = () => {
    setIsChatbotExpanded(!isChatbotExpanded);
  };

  const toggleSurvey = () => {
    setIsSurveyExpanded(!isSurveyExpanded);
  };

  // Touch event handlers for drawer drag
  const handleTouchStart = (e) => {
    touchStartY.current = e.touches[0].clientY;
    touchStartTime.current = Date.now();
    setIsDragging(true);
  };

  const handleTouchMove = (e) => {
    if (!touchStartY.current) return;
    
    const currentY = e.touches[0].clientY;
    const diff = touchStartY.current - currentY; // Positive = swipe up, negative = swipe down
    
    // Apply constraints based on current state
    if (isChatbotExpanded) {
      // When expanded, only allow dragging down (closing)
      if (diff < 0) {
        setDrawerDragOffset(diff);
      }
    } else {
      // When collapsed, only allow dragging up (opening)
      if (diff > 0) {
        setDrawerDragOffset(-diff);
      }
    }
  };

  const handleTouchEnd = (e) => {
    if (!touchStartY.current) return;
    
    const touchEndY = e.changedTouches[0].clientY;
    const diff = touchStartY.current - touchEndY;
    const touchDuration = Date.now() - touchStartTime.current;
    const velocity = Math.abs(diff) / touchDuration; // pixels per ms
    
    // Thresholds for determining if drawer should toggle
    const swipeThreshold = 50; // minimum pixels to swipe
    const velocityThreshold = 0.5; // minimum velocity for quick swipes
    
    let shouldToggle = false;
    
    // Fast swipe - prioritize velocity
    if (velocity > velocityThreshold) {
      if (diff > 0 && !isChatbotExpanded) {
        // Fast swipe up while collapsed -> expand
        shouldToggle = true;
      } else if (diff < 0 && isChatbotExpanded) {
        // Fast swipe down while expanded -> collapse
        shouldToggle = true;
      }
    } 
    // Slow drag - check distance
    else if (Math.abs(diff) > swipeThreshold) {
      if (diff > 0 && !isChatbotExpanded) {
        // Slow drag up while collapsed -> expand
        shouldToggle = true;
      } else if (diff < 0 && isChatbotExpanded) {
        // Slow drag down while expanded -> collapse
        shouldToggle = true;
      }
    }
    
    if (shouldToggle) {
      setIsChatbotExpanded(!isChatbotExpanded);
    }
    
    // Reset drag state
    setDrawerDragOffset(0);
    setIsDragging(false);
    touchStartY.current = null;
    touchStartTime.current = null;
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showExplore, filters]);

  if (!showExplore) {
    return (
      <div className="app">
        <Header 
          currentView="home"
          hasConsented={hasConsented}
          onNavigateToExplore={handleNavigateToExplore}
          onNavigateToHome={handleNavigateToHome}
        />
        <div className="landing-page">
          <div className="landing-content">
            <div className="museum-label">AUSTRALIAN MUSEUM</div>
            <h1 className="main-title">COLLECTION EXPLORER</h1>
            <div className="landing-nav">
              <span className="nav-item">Digitised Specimen Records on Map</span>
              <span className="nav-divider">•</span>
              <span className="nav-item">AI Chat Assistant</span>
            </div>
            <button 
              className={`start-button ${!hasConsented ? 'disabled' : ''}`}
              onClick={handleStartExploring}
            >
              START EXPLORING
            </button>
            
            {/* Consent Section */}
            <div className={`consent-section ${shakeConsent ? 'shake' : ''}`}>
              <div className="consent-checkbox-row">
                <input
                  type="checkbox"
                  id="consent-checkbox"
                  className="consent-checkbox"
                  checked={hasConsented}
                  onChange={handleConsentChange}
                />
                <label htmlFor="consent-checkbox" className="consent-label">
                  I have read the participant information statement and consent form, and I give my consent in participating in this research study
                </label>
              </div>
              <div className="consent-link-row">
                {/* TODO: Replace with your OneDrive URL */}
                <a 
                  href="https://studentutsedu-my.sharepoint.com/:b:/g/personal/yiyuan_wang_uts_edu_au/EWU_FHTquEFNjBjDneMbeBUBg6pDcTHM0YJWjHqmqnx4GQ?e=V6Weeg" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="consent-document-link"
                >
                  Participant Information Statement and Consent Form
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <Header 
        currentView="explore"
        hasConsented={hasConsented}
        onNavigateToExplore={handleNavigateToExplore}
        onNavigateToHome={handleNavigateToHome}
      />
      <div className="main-content">
        <div className="left-panel">
          <MapView 
            occurrences={occurrences}
            loading={loading}
            initialLoading={initialLoading}
            onBoundsChange={handleBoundsChange}
            totalInViewport={totalInViewport}
            filters={filters}
            facets={facets}
            onFilterChange={handleFilterChange}
          />
        </div>
        
        {/* Desktop view - side panel */}
        <div className="right-panel desktop-only">
          <Chatbot />
        </div>

        {/* Mobile view - bottom sheet */}
        <div 
          ref={drawerRef}
          className={`chatbot-drawer mobile-only ${isChatbotExpanded ? 'expanded' : 'collapsed'} ${isDragging ? 'dragging' : ''}`}
          style={{
            transform: `translateY(${drawerDragOffset}px)`,
            transition: isDragging ? 'none' : 'transform 0.3s ease, height 0.3s ease'
          }}
        >
          <div 
            className="drawer-handle" 
            onClick={toggleChatbot}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
          >
            <div className="handle-bar"></div>
            {isChatbotExpanded ? (
              <div className="drawer-label">✕ Close Chat</div>
            ) : (
              <div className="drawer-preview">
                <div className="drawer-preview-title">💬 Tap to chat with AI Assistant</div>
                <div className="drawer-preview-text">
                  I can help answer questions about the collection and identify animals from photos
                </div>
                <div className="drawer-preview-action"></div>
              </div>
            )}
          </div>
          <div className="drawer-content">
            <Chatbot />
          </div>
        </div>

        {/* Floating Survey Component */}
        <div className={`floating-survey ${isSurveyExpanded ? 'expanded' : 'collapsed'}`}>
          {/* Collapsed tab */}
          <div className="survey-tab" onClick={toggleSurvey}>
            <span className="survey-tab-text">Take Survey</span>
          </div>
          
          {/* Expanded content */}
          <div className="survey-content">
            <button className="survey-close" onClick={toggleSurvey}>✕</button>
            <div className="survey-text">We would appreciate it if you could fill out this survey after interacting with the application.</div>
            <a 
              href="https://qualtricsxmv4ln2spch.qualtrics.com/jfe/form/SV_bmvLUlly98nRlOu" 
              target="_blank" 
              rel="noopener noreferrer"
              className="survey-button"
            >
              📋 Take Survey
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;