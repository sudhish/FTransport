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
import { Add as AddIcon, Clear as ClearIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

import { useTransfer } from '../context/TransferContext.tsx';
import { api } from '../services/api.ts';
import TransferForm from './TransferForm.tsx';
import TransferCard from './TransferCard.tsx';
import { uiLogger } from '../utils/logger.ts';
import { TransferMode } from '../types/index.ts';

const Dashboard: React.FC = () => {
  const { state, dispatch } = useTransfer();
  const [showForm, setShowForm] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadTransfers();
  }, []);

  const loadTransfers = async () => {
    try {
      uiLogger.info('Loading transfers from API');
      dispatch({ type: 'SET_LOADING', payload: true });
      const transfers = await api.listTransfers();
      uiLogger.info(`Loaded ${transfers.length} transfers`);
      dispatch({ type: 'SET_TRANSFERS', payload: transfers });
    } catch (error) {
      uiLogger.error('Failed to load transfers', error);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to load transfers' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const handleCreateTransfer = async (sourceUrl: string, transferMode: TransferMode) => {
    try {
      uiLogger.info(`Creating new transfer for URL: ${sourceUrl} (mode: ${transferMode})`);
      dispatch({ type: 'SET_LOADING', payload: true });
      const newTransfer = await api.createTransfer({ 
        source_url: sourceUrl, 
        transfer_mode: transferMode 
      });
      uiLogger.info(`Transfer created successfully: ${newTransfer.id}`);
      dispatch({ type: 'ADD_TRANSFER', payload: newTransfer });
      setShowForm(false);
      navigate(`/transfer/${newTransfer.id}`);
    } catch (error) {
      uiLogger.error('Failed to create transfer', error);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to create transfer' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const handleViewTransfer = (transferId: string) => {
    navigate(`/transfer/${transferId}`);
  };

  const handleClearCompleted = async () => {
    try {
      uiLogger.info('Clearing completed transfers');
      dispatch({ type: 'SET_LOADING', payload: true });
      const result = await api.clearCompletedTransfers();
      uiLogger.info(`Successfully cleared ${result.cleared_count} completed transfers`);
      dispatch({ type: 'SET_ERROR', payload: null }); // Clear any existing errors
      // Reload transfers to reflect changes
      await loadTransfers();
      // Show success message
      dispatch({ 
        type: 'SET_ERROR', 
        payload: `Successfully cleared ${result.cleared_count} completed transfers` 
      });
      // Clear success message after 3 seconds
      setTimeout(() => {
        dispatch({ type: 'SET_ERROR', payload: null });
      }, 3000);
    } catch (error) {
      uiLogger.error('Failed to clear completed transfers', error);
      dispatch({ type: 'SET_ERROR', payload: 'Failed to clear completed transfers' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const hasCompletedTransfers = state.transfers.some(transfer => 
    ['completed', 'failed', 'cancelled'].includes(transfer.status)
  );

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Data Transfer Dashboard
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<ClearIcon />}
            onClick={handleClearCompleted}
            disabled={state.loading || !hasCompletedTransfers}
            color="secondary"
          >
            Clear Completed
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setShowForm(true)}
            disabled={state.loading}
          >
            New Transfer
          </Button>
        </Box>
      </Box>

      {state.error && (
        <Alert 
          severity={state.error.includes('Successfully') ? 'success' : 'error'} 
          sx={{ mb: 3 }}
        >
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