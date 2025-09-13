import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Grid,
  Alert,
  CircularProgress
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

import { useTransfer } from '../context/TransferContext.tsx';
import { api } from '../services/api.ts';
import TransferForm from './TransferForm.tsx';
import TransferCard from './TransferCard.tsx';

const Dashboard: React.FC = () => {
  const { state, dispatch } = useTransfer();
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadTransfers();
  }, []);

  const loadTransfers = async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const transfers = await api.listTransfers();
      dispatch({ type: 'SET_TRANSFERS', payload: transfers });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to load transfers' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const handleCreateTransfer = async (sourceUrl: string) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const newTransfer = await api.createTransfer({ source_url: sourceUrl });
      dispatch({ type: 'ADD_TRANSFER', payload: newTransfer });
      setShowForm(false);
      navigate(`/transfer/${newTransfer.id}`);
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to create transfer' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const handleViewTransfer = (transferId: string) => {
    navigate(`/transfer/${transferId}`);
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Data Transfer Dashboard
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setShowForm(true)}
          disabled={state.loading}
        >
          New Transfer
        </Button>
      </Box>

      {state.error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {state.error}
        </Alert>
      )}

      {showForm && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <TransferForm
              onSubmit={handleCreateTransfer}
              onCancel={() => setShowForm(false)}
              loading={state.loading}
            />
          </CardContent>
        </Card>
      )}

      {state.loading && !showForm ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {state.transfers.length === 0 ? (
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" textAlign="center" color="text.secondary">
                    No transfers yet. Click "New Transfer" to get started.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ) : (
            state.transfers.map((transfer) => (
              <Grid item xs={12} md={6} lg={4} key={transfer.id}>
                <TransferCard
                  transfer={transfer}
                  onClick={() => handleViewTransfer(transfer.id)}
                />
              </Grid>
            ))
          )}
        </Grid>
      )}
    </Box>
  );
};

export default Dashboard;