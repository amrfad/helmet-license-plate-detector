import React, { useState } from 'react';
import VideoFeed from './components/VideoFeed';
import ControlPanel from './components/ControlPanel';
import LogViewer from './components/LogViewer';
import './App.css';

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(Date.now());

  const handleConfigChange = () => {
    // Update trigger to reload video feed
    setRefreshTrigger(Date.now());
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Helmet & License Plate Detection System</h1>
        <div className="status-indicator">System Active</div>
      </header>

      <main className="main-content">
        <div className="left-column">
          <VideoFeed refreshTrigger={refreshTrigger} />
        </div>

        <div className="right-column">
          {/* Controls moved to sidebar for better visibility */}
          <ControlPanel onConfigChange={handleConfigChange} />
          <LogViewer />
        </div>
      </main>
    </div>
  );
}

export default App;
