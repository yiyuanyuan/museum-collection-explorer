import React from 'react';
import './Header.css';

function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <svg className="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 21h18"></path>
            <path d="M5 21V7l7-4 7 4v14"></path>
            <path d="M9 21v-6h6v6"></path>
          </svg>
          <span className="logo-text">COLLECTION EXPLORER</span>
        </div>
        <nav className="nav">
          <a href="/" className="nav-link">HOME</a>
          <a href="#explore" className="nav-link active">EXPLORE</a>
        </nav>
      </div>
    </header>
  );
}

export default Header;