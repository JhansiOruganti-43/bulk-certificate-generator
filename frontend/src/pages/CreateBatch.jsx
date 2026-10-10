import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, Plus, Trash2, CheckCircle } from 'lucide-react';
import { createBatch } from '../api';
import './CreateBatch.css';

const CreateBatch = () => {
  const navigate = useNavigate();
  const [recipients, setRecipients] = useState([
    { recipient_name: '', recipient_email: '', course_name: '' }
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleAddRecipient = () => {
    setRecipients([...recipients, { recipient_name: '', recipient_email: '', course_name: '' }]);
  };

  const handleRemoveRecipient = (index) => {
    if (recipients.length > 1) {
      setRecipients(recipients.filter((_, i) => i !== index));
    }
  };

  const handleChange = (index, field, value) => {
    const newRecipients = [...recipients];
    newRecipients[index][field] = value;
    setRecipients(newRecipients);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      // Basic validation
      const invalid = recipients.some(r => !r.recipient_name || !r.recipient_email || !r.course_name);
      if (invalid) {
        throw new Error('Please fill in all fields for all recipients.');
      }

      const response = await createBatch({ recipients });
      navigate(`/batches/${response.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to create batch');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="create-batch-page">
      <h1 className="page-title">Create Certificate Batch</h1>
      
      <div className="create-batch-layout">
        <div className="card form-card">
          <h2 className="section-title">Recipient Details</h2>
          
          {error && (
            <div className="alert alert-error">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="recipients-list">
              {recipients.map((recipient, index) => (
                <div key={index} className="recipient-row">
                  <div className="row-number">{index + 1}</div>
                  <div className="row-fields">
                    <div className="field-group">
                      <label>Name</label>
                      <input 
                        type="text"
                        placeholder="John Doe"
                        value={recipient.recipient_name}
                        onChange={(e) => handleChange(index, 'recipient_name', e.target.value)}
                        required
                      />
                    </div>
                    <div className="field-group">
                      <label>Email</label>
                      <input 
                        type="email"
                        placeholder="john@example.com"
                        value={recipient.recipient_email}
                        onChange={(e) => handleChange(index, 'recipient_email', e.target.value)}
                        required
                      />
                    </div>
                    <div className="field-group">
                      <label>Course / Event</label>
                      <input 
                        type="text"
                        placeholder="React Masterclass"
                        value={recipient.course_name}
                        onChange={(e) => handleChange(index, 'course_name', e.target.value)}
                        required
                      />
                    </div>
                  </div>
                  {recipients.length > 1 && (
                    <button 
                      type="button" 
                      className="btn-remove"
                      onClick={() => handleRemoveRecipient(index)}
                      title="Remove recipient"
                    >
                      <Trash2 size={18} />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <div className="form-actions-row">
              <button 
                type="button" 
                className="btn btn-secondary btn-outline" 
                onClick={handleAddRecipient}
              >
                <Plus size={18} style={{ marginRight: '0.5rem' }} /> Add Row
              </button>
            </div>

            <div className="form-submit-area">
              <button 
                type="submit" 
                className="btn btn-primary btn-large"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>Generating...</>
                ) : (
                  <>
                    <CheckCircle size={20} style={{ marginRight: '0.5rem' }} /> 
                    Submit Batch
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        <div className="info-sidebar">
          <div className="card info-card">
            <h3>Batch Processing</h3>
            <p className="text-muted">
              Enter recipient details manually. Each recipient will receive a customized PDF certificate.
            </p>
            <div className="info-tips">
              <div className="info-tip">
                <strong>Instant Generation:</strong> PDFs are processed immediately.
              </div>
              <div className="info-tip">
                <strong>Fault Tolerant:</strong> If one certificate fails, the rest will continue processing.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateBatch;
