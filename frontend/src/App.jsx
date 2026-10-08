import { useState, useEffect } from 'react'
import './styles/theme.css'

function App() {
  const [health, setHealth] = useState({ status: 'loading...', message: '' });
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/health')
      .then(res => {
        if (!res.ok) throw new Error('API returned an error');
        return res.json();
      })
      .then(data => setHealth(data))
      .catch(err => setError(err.message));
  }, []);

  return (
    <div className="container">
      <header className="header">
        <h1>AEREO Bulk Certificate Generator API</h1>
        <p className="subtitle">Phase 1: Project Setup</p>
      </header>

      <main className="main-content">
        <div className="status-card">
          <h2>Backend API Status</h2>
          {error ? (
            <div className="status error">
              <span className="indicator"></span> Error connecting to backend: {error}
            </div>
          ) : (
            <div className={`status ${health.status === 'ok' ? 'success' : 'pending'}`}>
              <span className="indicator"></span> {health.message || 'Connecting...'}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
