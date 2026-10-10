export default function ProgressBar({ percent, label }) {
  const clamped = Math.max(0, Math.min(100, isNaN(percent) ? 0 : percent));
  
  return (
    <div style={{ margin: '1.5rem 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '.5rem', fontSize: '0.875rem', fontWeight: 500 }}>
        <span>{label}</span>
        <span>{clamped}%</span>
      </div>
      <div style={{ 
        width: '100%', 
        height: '8px', 
        backgroundColor: 'var(--color-border)',
        borderRadius: '4px',
        overflow: 'hidden'
      }}>
        <div style={{
          height: '100%',
          width: `${clamped}%`,
          backgroundColor: 'var(--color-primary)',
          transition: 'width 0.5s ease-out'
        }} />
      </div>
    </div>
  );
}
