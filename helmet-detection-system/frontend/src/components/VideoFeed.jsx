import React from 'react';

const VideoFeed = ({ refreshTrigger }) => {
    // We use a timestamp to force refresh if needed, but MJPEG stream usually auto-updates.
    // Sometimes browsers cache or disconnect. 
    // A simple img src is usually enough for local dev.
    const streamUrl = `http://localhost:5000/video_feed?t=${refreshTrigger}`;

    return (
        <div className="video-feed-container">
            <h2>Live Feed</h2>
            <div className="video-wrapper">
                <img
                    src={streamUrl}
                    alt="Video Feed"
                    key={refreshTrigger}
                    onError={(e) => { e.target.src = "https://via.placeholder.com/640x480?text=No+Signal"; }}
                    style={{ width: '100%', borderRadius: '8px', border: '1px solid #444' }}
                />
            </div>
        </div>
    );
};

export default VideoFeed;
