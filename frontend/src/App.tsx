import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Container, AppBar, Toolbar, Typography } from '@mui/material';
import Dashboard from './components/Dashboard.tsx';
import TransferDetail from './components/TransferDetail.tsx';
import { TransferProvider } from './context/TransferContext.tsx';

function App() {
  return (
    <TransferProvider>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            FTransport - Data Migration Platform
          </Typography>
        </Toolbar>
      </AppBar>
      
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transfer/:transferId" element={<TransferDetail />} />
        </Routes>
      </Container>
    </TransferProvider>
  );
}

export default App;