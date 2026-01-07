import React, { useState } from 'react';
import axios from 'axios';

const ControlPanel = ({ onConfigChange }) => {
    const [mode, setMode] = useState('webcam');
    const [value, setValue] = useState('0');
    const [status, setStatus] = useState('');

    const applyConfig = async () => {
        try {
            setStatus('Updating...');
            const res = await axios.post('http://localhost:5000/api/config', {
                mode,
                value
            });
            setStatus(`Updated: ${res.data.mode}`);
            if (onConfigChange) onConfigChange();
        } catch (err) {
            setStatus('Error updating config');
            console.error(err);
        }
    };

    return (
        <div className="control-panel">
            <h3>Configuration</h3>
            <div className="form-group">
                <label>Input Mode:</label>
                <select value={mode} onChange={(e) => setMode(e.target.value)}>
                    <option value="webcam">Webcam</option>
                    <option value="file">Video File</option>
                    <option value="rtsp">RTSP Stream</option>
                </select>
            </div>

            <div className="form-group">
                <label>Input Value (Index/Path/URL):</label>
                <input
                    type="text"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    placeholder={mode === 'webcam' ? "0" : "Path or URL"}
                />
            </div>

            <button onClick={applyConfig} className="btn-primary">Apply Configuration</button>
            {status && <p className="status-msg">{status}</p>}
        </div>
    );
};

export default ControlPanel;
