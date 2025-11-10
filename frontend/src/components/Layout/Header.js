import React from 'react';
import './Header.css';

function Header({ currentView, hasConsented, onNavigateToExplore, onNavigateToHome }) {
  const handleExploreClick = (e) => {
    e.preventDefault();
    onNavigateToExplore();
  };

  const handleHomeClick = (e) => {
    e.preventDefault();
    onNavigateToHome();
  };

  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <svg className="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 21h18"></path>
            <path d="M5 21V7l7-4 7 4v14"></path>
            <path d="M9 21v-6h6v6"></path>
          </svg>
          <span className="logo-text">COLLECTION EXPLORER (Testing)</span>
        </div>
        <nav className="nav">
          <a 
            href="#home" 
            className={`nav-link ${currentView === 'home' ? 'active' : ''}`}
            onClick={handleHomeClick}
          >
            HOME
          </a>
          <a 
            href="#explore" 
            className={`nav-link ${currentView === 'explore' ? 'active' : ''} ${!hasConsented ? 'disabled' : ''}`}
            onClick={handleExploreClick}
          >
            EXPLORE
          </a>
        </nav>
      </div>
    </header>
  );
}

export default Header;