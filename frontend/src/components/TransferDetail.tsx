import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  LinearProgress,
  Alert,
  Chip,
  Grid,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  CircularProgress
} from '@mui/material';
import {
  ArrowBack,
  CloudDone,
  Error,
  Pending,
  Sync,
  Cancel,
  Description
} from '@mui/icons-material';

import { useTransfer } from '../context/TransferContext.tsx';
import { transferLogger, websocketLogger } from '../utils/logger.ts';
import { useWebSocket } from '../hooks/useWebSocket.ts';
import { api } from '../services/api.ts';
import { Transfer, FileTransfer, TransferStatus } from '../types/index.ts';

const TransferDetail: React.FC = () => {
  const { transferId } = useParams<{ transferId: string }>();
  const navigate = useNavigate();
  const { state, dispatch } = useTransfer();
  const [files, setFiles] = useState<FileTransfer[]>([]);
  const [loading, setLoading] = useState(true);

  // WebSocket for real-time updates
  const { isConnected, lastProgress, error: wsError } = useWebSocket(transferId || null);

  useEffect(() => {
    if (transferId) {
      loadTransferDetails();
    }
  }, [transferId]);

  // Update transfer data when receiving WebSocket updates
  useEffect(() => {
    if (lastProgress && state.activeTransfer) {
      const updatedTransfer: Transfer = {
        ...state.activeTransfer,
        status: lastProgress.status,
        overall_progress: lastProgress.overall_progress,
        files_completed: lastProgress.files_completed,
        total_files: lastProgress.total_files,
        current_file_name: lastProgress.current_file?.name,
        current_file_progress: lastProgress.current_file?.progress || 0,
      };
      dispatch({ type: 'UPDATE_TRANSFER', payload: updatedTransfer });
    }
  }, [lastProgress, state.activeTransfer, dispatch]);

  const loadTransferDetails = async () => {
    if (!transferId) return;

    try {
      setLoading(true);
      const [transfer, transferFiles] = await Promise.all([
        api.getTransfer(transferId),
        api.getTransferFiles(transferId)
      ]);
      
      dispatch({ type: 'SET_ACTIVE_TRANSFER', payload: transfer });
      setFiles(transferFiles);
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to load transfer details' });
    } finally {
      setLoading(false);
    }
  };

  const handleCancelTransfer = async () => {
    if (!transferId || !state.activeTransfer) return;

    try {
      await api.cancelTransfer(transferId);
      const updatedTransfer = {
        ...state.activeTransfer,
        status: TransferStatus.CANCELLED
      };
      dispatch({ type: 'UPDATE_TRANSFER', payload: updatedTransfer });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to cancel transfer' });
    }
  };

  const getFileStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CloudDone color="success" />;
      case 'failed':
        return <Error color="error" />;
      case 'in_progress':
        return <Sync color="primary" />;
      case 'pending':
      default:
        return <Pending color="action" />;
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${Math.round(size * 100) / 100} ${units[unitIndex]}`;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Not started';
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" my={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (!state.activeTransfer) {
    return (
      <Box>
        <Alert severity="error">Transfer not found</Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/')} sx={{ mt: 2 }}>
          Back to Dashboard
        </Button>
      </Box>
    );
  }

  const transfer = state.activeTransfer;
  const canCancel = [TransferStatus.PENDING, TransferStatus.SCANNING, TransferStatus.TRANSFERRING, TransferStatus.UPLOADING].includes(transfer.status);

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/')}>
          Back to Dashboard
        </Button>
        {canCancel && (
          <Button variant="outlined" color="error" onClick={handleCancelTransfer}>
            Cancel Transfer
          </Button>
        )}
      </Box>

      {state.error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {state.error}
        </Alert>
      )}

      {wsError && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Real-time updates disconnected: {wsError}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Transfer Overview */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Transfer Details
              </Typography>
              
              <Box mb={2}>
                <Typography variant="body2" color="text.secondary">
                  Source URL:
                </Typography>
                <Typography variant="body1" sx={{ wordBreak: 'break-all' }}>
                  {transfer.source_url}
                </Typography>
              </Box>

              <Box mb={2}>
                <Chip
                  label={transfer.status.replace('_', ' ').toUpperCase()}
                  color={transfer.status === TransferStatus.COMPLETED ? 'success' : 
                         transfer.status === TransferStatus.FAILED ? 'error' : 'primary'}
                  variant="outlined"
                />
              </Box>

              {transfer.total_files > 0 && (
                <Box mb={2}>
                  <Typography variant="body2" gutterBottom>
                    Overall Progress: {transfer.files_completed} / {transfer.total_files} files 
                    ({Math.round(transfer.overall_progress)}%)
                  </Typography>
                  <LinearProgress variant="determinate" value={transfer.overall_progress} />
                </Box>
              )}

              {transfer.current_file_name && (
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">
                    Current File:
                  </Typography>
                  <Typography variant="body1">
                    {transfer.current_file_name}
                  </Typography>
                  {transfer.current_file_progress > 0 && (
                    <LinearProgress 
                      variant="determinate" 
                      value={transfer.current_file_progress} 
                      sx={{ mt: 1 }}
                    />
                  )}
                </Box>
              )}

              {transfer.error_message && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {transfer.error_message}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Transfer Info */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Transfer Info
              </Typography>
              
              <Typography variant="body2" color="text.secondary">
                Created: {formatDate(transfer.created_at)}
              </Typography>
              {transfer.started_at && (
                <Typography variant="body2" color="text.secondary">
                  Started: {formatDate(transfer.started_at)}
                </Typography>
              )}
              {transfer.completed_at && (
                <Typography variant="body2" color="text.secondary">
                  Completed: {formatDate(transfer.completed_at)}
                </Typography>
              )}
              
              <Divider sx={{ my: 2 }} />
              
              <Typography variant="body2" color="text.secondary">
                Real-time Updates: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
              </Typography>
              
              {transfer.notebooklm_notebook_id && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" color="text.secondary">
                    NotebookLM ID: {transfer.notebooklm_notebook_id}
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* File List */}
        {files.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Files ({files.length})
                </Typography>
                <List>
                  {files.map((file, index) => (
                    <React.Fragment key={index}>
                      <ListItem>
                        <ListItemIcon>
                          {getFileStatusIcon(file.status)}
                        </ListItemIcon>
                        <ListItemText
                          primary={file.file_name}
                          secondary={
                            <Box>
                              <Typography variant="caption" component="span">
                                Status: {file.status} | Size: {formatFileSize(file.file_size)}
                              </Typography>
                              {file.status === 'in_progress' && file.bytes_transferred > 0 && (
                                <Typography variant="caption" component="div">
                                  Transferred: {formatFileSize(file.bytes_transferred)}
                                </Typography>
                              )}
                              {file.error_message && (
                                <Typography variant="caption" color="error" component="div">
                                  Error: {file.error_message}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < files.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default TransferDetail;