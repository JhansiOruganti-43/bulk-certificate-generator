import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Layers, FileText, CheckCircle, XCircle, ArrowRight } from 'lucide-react';
import { fetchDashboardStats, fetchBatches } from '../api';
import './Dashboard.css';
import { format } from 'date-fns';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [recentBatches, setRecentBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [statsRes, batchesRes] = await Promise.all([
          fetchDashboardStats(),
          fetchBatches({ limit: 5 })
        ]);
        setStats(statsRes.data);
        setRecentBatches(batchesRes.data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch dashboard data', err);
        setError('Failed to load dashboard data. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-state">
        <XCircle size={48} className="error-icon" />
        <p>{error}</p>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <h1 className="page-title">Overview</h1>
      
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon-wrapper teal">
            <Layers size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Batches</p>
            <h3 className="stat-value">{stats?.total_batches || 0}</h3>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon-wrapper sky">
            <FileText size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Total Certificates</p>
            <h3 className="stat-value">{stats?.total_certificates || 0}</h3>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon-wrapper gold">
            <CheckCircle size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Success Rate</p>
            <h3 className="stat-value">{stats?.success_rate || 0}%</h3>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon-wrapper red">
            <XCircle size={24} />
          </div>
          <div className="stat-content">
            <p className="stat-label">Failed Certificates</p>
            <h3 className="stat-value">{stats?.failed_certificates || 0}</h3>
          </div>
        </div>
      </div>

      <div className="recent-batches-section">
        <div className="section-header">
          <h2 className="section-title">Recent Batches</h2>
          <Link to="/batches/create" className="btn btn-primary">
            Create New Batch
          </Link>
        </div>
        
        <div className="card">
          {recentBatches.length === 0 ? (
            <div className="empty-state">
              <Layers size={48} strokeWidth={1} />
              <h3>No batches found</h3>
              <p>You haven't generated any certificate batches yet.</p>
              <Link to="/batches/create" className="btn btn-primary mt-4">
                Create Your First Batch
              </Link>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Batch ID</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Progress</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {recentBatches.map(batch => (
                    <tr key={batch.id}>
                      <td>
                        <Link to={`/batches/${batch.id}`} className="batch-id-link">
                          {batch.id.substring(0, 8)}...
                        </Link>
                      </td>
                      <td>{format(new Date(batch.created_at), 'MMM d, yyyy HH:mm')}</td>
                      <td>
                        <span className={`status-badge status-${batch.status}`}>
                          {batch.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td>
                        <div className="progress-wrapper">
                          <div className="progress-bar-bg">
                            <div 
                              className="progress-bar-fill" 
                              style={{ width: `${batch.progress_percentage}%` }}
                            ></div>
                          </div>
                          <span className="progress-text">{batch.progress_percentage}%</span>
                        </div>
                      </td>
                      <td>
                        <Link to={`/batches/${batch.id}`} className="btn-icon">
                          <ArrowRight size={18} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
