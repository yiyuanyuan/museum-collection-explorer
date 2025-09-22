#!/bin/bash

# Create all necessary React component files
touch src/App.js
touch src/App.css
touch src/index.js
touch src/index.css
touch src/reportWebVitals.js

# Create component files
touch src/components/Map/MapView.js
touch src/components/Map/MapView.css
touch src/components/Map/RecordPopup.js
touch src/components/Filters/FilterPanel.js
touch src/components/Filters/FilterPanel.css
touch src/components/Statistics/Statistics.js
touch src/components/Statistics/Statistics.css
touch src/components/Chatbot/Chatbot.js
touch src/components/Chatbot/Chatbot.css
touch src/components/Layout/Header.js
touch src/components/Layout/Header.css

# Create service files
touch src/services/api.js
touch src/services/biocache.js

# Create public files
touch public/index.html
touch public/manifest.json
touch public/service-worker.js

echo "All files created successfully!"
