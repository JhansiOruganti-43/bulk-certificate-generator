export default function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div style={{
      backgroundColor: '#fdf6e3',
      color: '#8a6d3b',
      borderLeft: '4px solid var(--color-gold)',
      padding: '1rem',
      marginBottom: '1rem',
      borderRadius: '4px'
    }}>
      <strong>Error:</strong> {message}
    </div>
  );
}
