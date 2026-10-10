import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchBatches } from '../api';
import LoadingSkeleton from '../components/LoadingSkeleton';
import ErrorBanner from '../components/ErrorBanner';

function StatusBadge({ status }) {
  const map = {
    completed:             { color: 'var(--color-primary)',   label: 'Completed' },
    completed_with_errors: { color: 'var(--color-gold)',      label: 'Partial' },
    failed:                { color: '#dc2626',                label: 'Failed' },
    processing:            { color: 'var(--color-secondary)', label: 'Processing' },
    pending:               { color: 'var(--color-text-muted)',label: 'Pending' },
  };
  const { color, label } = map[status] || { color: 'var(--color-text-muted)', label: status };
  return (
    <span style={{
      padding: '0.2rem 0.65rem', borderRadius: '1rem',
      fontSize: '0.78rem', fontWeight: 600,
      backgroundColor: `${color}22`, color,
      textTransform: 'uppercase', letterSpacing: '0.04em'
    }}>{label}</span>
  );
}

export default function BatchHistory() {
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    fetchBatches({ skip: 0, limit: 100 })
      .then(r => setBatches(Array.isArray(r.data) ? r.data : []))
      .catch(e => setError(e.response?.data?.detail || e.message || 'Failed to load batch history'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="container"><LoadingSkeleton rows={6} /></div>;

  return (
    <div className="container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2 className="section-title" style={{ margin: 0 }}>Batch History</h2>
        <Link to="/batches/new" className="btn btn-primary">+ Create Batch</Link>
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {batches.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>
            <p style={{ fontSize: '3rem', margin: '0 0 1rem' }}>📋</p>
            <p style={{ fontWeight: 600, color: 'var(--color-text-primary)', margin: '0 0 0.5rem' }}>No batches yet</p>
            <p style={{ margin: '0 0 1.5rem' }}>Create your first batch to get started.</p>
            <Link to="/batches/new" className="btn btn-primary">Create Batch</Link>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Batch ID</th>
                  <th>Status</th>
                  <th>Total</th>
                  <th>Successful</th>
                  <th>Failed</th>
                  <th>Progress</th>
                  <th>Created</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {batches.map(b => (
                  <tr key={b.id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                      {b.id.slice(0, 8)}…
                    </td>
                    <td><StatusBadge status={b.status} /></td>
                    <td style={{ fontWeight: 600 }}>{b.total_recipients}</td>
                    <td style={{ color: 'var(--color-primary)', fontWeight: 600 }}>{b.successful_certificates}</td>
                    <td style={{ color: b.failed_certificates > 0 ? 'var(--color-gold)' : 'var(--color-text-muted)', fontWeight: 600 }}>
                      {b.failed_certificates}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ flex: 1, height: '6px', backgroundColor: 'var(--color-border)', borderRadius: '3px', minWidth: '60px' }}>
                          <div style={{
                            height: '100%',
                            width: `${b.progress_percentage}%`,
                            backgroundColor: 'var(--color-primary)',
                            borderRadius: '3px'
                          }} />
                        </div>
                        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>{b.progress_percentage}%</span>
                      </div>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                      {new Date(b.created_at).toLocaleString()}
                    </td>
                    <td>
                      <Link to={`/batches/${b.id}`} className="btn btn-secondary"
                        style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem' }}>
                        View Details
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
  );
}
