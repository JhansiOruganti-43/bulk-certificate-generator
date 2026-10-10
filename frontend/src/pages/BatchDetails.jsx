import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, Clock, Download } from 'lucide-react';
import { fetchBatchDetails, fetchBatchProgress, downloadCertificate, fetchBatchCertificates } from '../api';
import './BatchDetails.css';

const BatchDetails = () => {
  const { id } = useParams();
  const [batch, setBatch] = useState(null);
  const [progress, setProgress] = useState(null);
  const [certificates, setCertificates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(null);

  useEffect(() => {
    let intervalId;

    const loadBatch = async () => {
      try {
        // Fetch all three in parallel; surface the real server error message if any fails
        const [batchRes, progRes, certsRes] = await Promise.all([
          fetchBatchDetails(id),
          fetchBatchProgress(id),
          fetchBatchCertificates(id),
        ]);

        setBatch(batchRes.data);
        setProgress(progRes.data);
        setCertificates(certsRes.data);
        setError(null);

        // If processing, poll every 2s
        if (progRes.data.status === 'pending' || progRes.data.status === 'processing') {
          intervalId = setInterval(pollProgress, 2000);
        }
      } catch (err) {
        console.error('Failed to load batch details:', err);
        // Show the actual server error if available
        const serverMsg =
          err?.response?.data?.detail ||
          err?.message ||
          'Failed to load batch details.';
        setError(serverMsg);
      } finally {
        setLoading(false);
      }
    };

    const pollProgress = async () => {
      try {
        const progRes = await fetchBatchProgress(id);
        setProgress(progRes.data);

        if (progRes.data.status !== 'pending' && progRes.data.status !== 'processing') {
          clearInterval(intervalId);
          // Reload certs when finished
          const certsRes = await fetchBatchCertificates(id);
          setCertificates(certsRes.data);
        }
      } catch (err) {
        console.error('Failed to poll progress', err);
      }
    };

    loadBatch();

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [id]);

  const handleDownload = async (certId, name) => {
    try {
      setDownloading(certId);
      const res = await downloadCertificate(certId);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${name}_certificate.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error('Failed to download certificate', err);
      alert('Failed to download certificate');
    } finally {
      setDownloading(null);
    }
  };

  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner"></div>
        <p>Loading batch details...</p>
      </div>
    );
  }

  if (error || !progress) {
    return (
      <div className="error-state">
        <XCircle size={48} className="error-icon" />
        <p>{error || "Batch not found"}</p>
        <Link to="/dashboard" className="btn btn-primary mt-4">Return to Dashboard</Link>
      </div>
    );
  }

  const isComplete = progress.status !== 'pending' && progress.status !== 'processing';

  return (
    <div className="batch-details-page">
      <div className="page-header">
        <Link to="/dashboard" className="back-link">
          <ArrowLeft size={18} /> Back to Dashboard
        </Link>
        <h1 className="page-title">Batch Processing Details</h1>
      </div>

      <div className="progress-card card">
        <div className="progress-header">
          <div>
            <h3>Batch ID: <span className="batch-id">{id}</span></h3>
            <span className={`status-badge status-${progress.status}`}>
              {progress.status.replace(/_/g, ' ')}
            </span>
          </div>
          <div className="progress-percentage">
            {progress.progress_percentage}% completed
          </div>
        </div>

        <div className="progress-bar-container">
          <div className="progress-bar">
            <div 
              className={`progress-fill ${isComplete ? (progress.failed > 0 ? 'fill-warning' : 'fill-success') : ''}`}
              style={{ width: `${progress.progress_percentage}%` }}
            ></div>
          </div>
        </div>

        <div className="stats-row">
          <div className="stat-box">
            <span className="stat-value">{progress.total}</span>
            <span className="stat-label">Total</span>
          </div>
          <div className="stat-box">
            <span className="stat-value text-blue">{progress.processed}</span>
            <span className="stat-label">Processed</span>
          </div>
          <div className="stat-box">
            <span className="stat-value text-green">{progress.successful}</span>
            <span className="stat-label">Successful</span>
          </div>
          <div className="stat-box">
            <span className="stat-value text-red">{progress.failed}</span>
            <span className="stat-label">Failed</span>
          </div>
        </div>
      </div>

      <div className="certificates-section">
        <h2 className="section-title">Certificates</h2>
        
        <div className="card">
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Recipient Name</th>
                  <th>Email</th>
                  <th>Course</th>
                  <th>Status</th>
                  <th>Actions / Info</th>
                </tr>
              </thead>
              <tbody>
                {certificates.map(cert => (
                  <tr key={cert.id}>
                    <td>{cert.recipient_name}</td>
                    <td>{cert.recipient_email}</td>
                    <td>{cert.course_name}</td>
                    <td>
                      <span className={`status-badge status-${cert.status}`}>
                        {cert.status}
                      </span>
                    </td>
                    <td>
                      {cert.status === 'completed' && (
                        <button 
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleDownload(cert.id, cert.recipient_name.replace(/\s+/g, '_'))}
                          disabled={downloading === cert.id}
                        >
                          {downloading === cert.id ? (
                            <Clock size={16} className="spin-icon" /> 
                          ) : (
                            <Download size={16} />
                          )}
                          <span style={{ marginLeft: '4px' }}>Download</span>
                        </button>
                      )}
                      {cert.status === 'failed' && (
                        <div className="error-message tooltip">
                          <XCircle size={16} /> Error
                          <span className="tooltip-text">{cert.error_message || "Generation failed"}</span>
                        </div>
                      )}
                      {(cert.status === 'pending' || cert.status === 'processing') && (
                        <span className="text-muted"><Clock size={16} style={{ verticalAlign: 'middle', marginRight: '4px' }}/> Waiting...</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BatchDetails;
