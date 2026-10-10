import { useParams } from 'react-router-dom';
import { downloadCertificate } from '../api';
import ErrorBanner from '../components/ErrorBanner';
import { useState } from 'react';

export default function CertificateViewer() {
  const { certId } = useParams();
  const [error, setError] = useState(null);

  const handleDownload = async () => {
    try {
      const response = await downloadCertificate(certId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `certificate_${certId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (e) {
      setError('Failed to download certificate.');
    }
  };

  return (
    <div className="container" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 className="section-title">Certificate: {certId}</h2>
        <button className="btn btn-secondary" onClick={handleDownload}>
          Download PDF
        </button>
      </div>
      {error && <ErrorBanner message={error} />}
      <div className="card" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--color-text-muted)' }}>
          To view this certificate in the browser, PDF rendering must be supported. You can download it using the button above.
        </p>
      </div>
    </div>
  );
}
