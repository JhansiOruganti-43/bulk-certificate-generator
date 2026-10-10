import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import CreateBatch from './pages/CreateBatch';
import BatchDetails from './pages/BatchDetails';
import BatchHistory from './pages/BatchHistory';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="batches/create" element={<CreateBatch />} />
          <Route path="batches/new" element={<CreateBatch />} />
          <Route path="batches/history" element={<BatchHistory />} />
          <Route path="batches/:id" element={<BatchDetails />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
