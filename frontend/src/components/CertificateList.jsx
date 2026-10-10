import { useEffect, useState } from 'react';
import axios from 'axios';

const BASE_URL = 'http://localhost:8000';

export default function CertificateList({ batchId }) {
  const [certs, setCerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState(null);
  const [downloadError, setDownloadError] = useState(null);

  useEffect(() => {
    axios.get(`${BASE_URL}/api/batches/${batchId}/certificates`)
      .then(r => setCerts(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [batchId]);

  const handleDownload = async (cert) => {
    setDownloadingId(cert.id);
    setDownloadError(null);
    try {
      // responseType:'blob' makes resp.data a native Blob already — do NOT re-wrap it
      const resp = await axios.get(
        `${BASE_URL}/api/certificates/${cert.id}/download`,
        { responseType: 'blob' }
      );
      // resp.data is a Blob; create an object URL directly from it
      const url = window.URL.createObjectURL(resp.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `certificate_${cert.certificate_id || cert.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      // Revoke after a short delay to ensure download starts
      setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    } catch (e) {
      const msg = e.response?.status === 404
        ? 'PDF file not found on server.'
        : e.response?.status === 400
        ? 'Certificate PDF not yet generated.'
        : `Download failed: ${e.message}`;
      setDownloadError(msg);
    } finally {
      setDownloadingId(null);
    }
  };

  if (loading) return null;
  const completed = certs.filter(c => c.status === 'completed');
  if (completed.length === 0) return null;

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', marginTop: '1.5rem' }}>
      <div style={{ padding: '1rem 1.5rem', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>Generated Certificates <span style={{ color: 'var(--color-primary)', fontWeight: 700 }}>({completed.length})</span></h3>
      </div>

      {downloadError && (
        <div style={{ padding: '0.75rem 1.5rem', backgroundColor: '#fef9ec', borderBottom: '1px solid var(--color-border)', color: '#92400e', borderLeft: '4px solid var(--color-gold)' }}>
          {downloadError}
        </div>
      )}

      <table className="table">
        <thead>
          <tr>
            <th>Recipient</th>
            <th>Email</th>
            <th>Course</th>
            <th>Certificate ID</th>
            <th>Download</th>
          </tr>
        </thead>
        <tbody>
          {completed.map(cert => (
            <tr key={cert.id}>
              <td style={{ fontWeight: 500 }}>{cert.recipient_name}</td>
              <td style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>{cert.recipient_email}</td>
              <td>{cert.course_name}</td>
              <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--color-secondary)' }}>
                {cert.certificate_id || '—'}
              </td>
              <td>
                <button
                  className="btn btn-primary"
                  style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}
                  onClick={() => handleDownload(cert)}
                  disabled={downloadingId === cert.id}
                >
                  {downloadingId === cert.id ? 'Downloading…' : '⬇ PDF'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
