import { useState, useRef } from 'react';

export default function FileDropzone({ onFileSelected, accept = ".csv" }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };
  
  const handleDragLeave = () => {
    setDragging(false);
  };
  
  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleClick = () => {
    inputRef.current.click();
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelected(e.target.files[0]);
    }
  };

  return (
    <div 
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      style={{
        border: `2px dashed ${dragging ? 'var(--color-primary)' : 'var(--color-border)'}`,
        borderRadius: '8px',
        padding: '2rem',
        textAlign: 'center',
        cursor: 'pointer',
        backgroundColor: dragging ? 'rgba(13, 159, 174, 0.05)' : 'var(--color-surface)',
        transition: 'all 0.2s'
      }}
    >
      <input 
        type="file" 
        accept={accept} 
        style={{ display: 'none' }} 
        ref={inputRef} 
        onChange={handleFileChange} 
      />
      <div style={{ color: 'var(--color-text-muted)' }}>
        <p style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>Click to upload or drag and drop</p>
        <p style={{ fontSize: '0.875rem' }}>CSV files only</p>
      </div>
    </div>
  );
}
