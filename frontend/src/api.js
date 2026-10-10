import axios from 'axios';

const BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

/* ---------- Dashboard stats ---------- */
export const fetchDashboardStats = () => api.get('/api/dashboard');

/* ---------- Batch endpoints ---------- */
export const createBatch = (payload) => api.post('/api/batches', payload);
export const fetchBatches = (params) => api.get('/api/batches', { params });
export const fetchBatchDetails = (batchId) => api.get(`/api/batches/${batchId}`);
export const fetchBatchProgress = (batchId) => api.get(`/api/batches/${batchId}/progress`);
export const downloadCertificate = (certId) => api.get(`/api/certificates/${certId}/download`, { responseType: 'blob' });
export const fetchBatchCertificates = (batchId) => api.get(`/api/batches/${batchId}/certificates`);

/* ---------- CSV validation (if backend supports) ---------- */
export const validateCsv = (file) => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/api/csv/validate', form, { headers: { 'Content-Type': 'multipart/form-data' } });
};
