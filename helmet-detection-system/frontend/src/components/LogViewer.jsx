import React, { useEffect, useState } from 'react';
import axios from 'axios';

const LogViewer = () => {
    const [logs, setLogs] = useState([]);

    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const res = await axios.get('http://localhost:5000/api/logs');
                // Newest first
                setLogs(res.data.reverse());
            } catch (err) {
                console.error("Failed to fetch logs", err);
            }
        };

        fetchLogs();
        const interval = setInterval(fetchLogs, 2000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="log-viewer">
            <h3>Detection Logs (No Helmet)</h3>
            <div className="log-list">
                {logs.length === 0 ? <p>No violations detected yet.</p> : logs.map((log, idx) => (
                    <div key={idx} className="log-item">
                        <div className="log-info">
                            <span className="timestamp">{new Date(log.timestamp).toLocaleTimeString()}</span>
                            <span className="plate-text">Plate: <strong>{log.plate_text}</strong></span>
                            <span className="conf">Conf: {(log.confidence * 100).toFixed(1)}%</span>
                        </div>
                        {log.image_path && (
                            <div className="log-img">
                                <img src={`http://localhost:5000${log.image_path}`} alt="License Plate" />
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default LogViewer;
