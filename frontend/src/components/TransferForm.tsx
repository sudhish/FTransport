import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import { api } from '../services/api.ts';
import { DriveType, TransferMode } from '../types/index.ts';

interface TransferFormProps {
  onSubmit: (sourceUrl: string, transferMode: TransferMode) => Promise<void>;
  onCancel: () => void;
  loading: boolean;
}

const TransferForm: React.FC<TransferFormProps> = ({ onSubmit, onCancel, loading }) => {
  const [sourceUrl, setSourceUrl] = useState('');
  const [transferMode, setTransferMode] = useState<TransferMode>(TransferMode.DIRECT_TO_NOTEBOOKLM);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleValidateUrl = async () => {
    if (!sourceUrl.trim()) {
      setError('Please enter a URL');
      return;
    }

    try {
      setValidating(true);
      setError(null);
      const result = await api.validateUrl(sourceUrl);
      setValidationResult(result);
      
      if (!result.valid) {
        setError(result.error_message || 'Invalid URL');
      }
    } catch (err) {
      setError('Failed to validate URL');
    } finally {
      setValidating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!sourceUrl.trim()) {
      setError('Please enter a URL');
      return;
    }

    if (!validationResult?.valid) {
      setError('Please validate the URL first');
      return;
    }

    try {
      await onSubmit(sourceUrl, transferMode);
    } catch (err) {
      setError('Failed to create transfer');
    }
  };

  const getDriveTypeLabel = (driveType: DriveType) => {
    switch (driveType) {
      case DriveType.GOOGLE_DRIVE:
        return 'Google Drive';
      case DriveType.ONEDRIVE:
        return 'OneDrive';
      case DriveType.DROPBOX:
        return 'Dropbox';
      default:
        return 'Unknown';
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 600 }}>
      <Typography variant="h6" gutterBottom>
        Create New Transfer
      </Typography>
      
      <TextField
        fullWidth
        label="Shared Drive URL"
        placeholder="Enter Google Drive, OneDrive, or Dropbox URL"
        value={sourceUrl}
        onChange={(e) => {
          setSourceUrl(e.target.value);
          setValidationResult(null);
          setError(null);
        }}
        margin="normal"
        required
        helperText="Example: https://drive.google.com/drive/folders/abc123"
      />

      <Box sx={{ mt: 2, mb: 2 }}>
        <Button
          variant="outlined"
          onClick={handleValidateUrl}
          disabled={!sourceUrl.trim() || validating}
          sx={{ mr: 2 }}
        >
          {validating ? <CircularProgress size={20} /> : 'Validate URL'}
        </Button>
        
        {validationResult && (
          <Box sx={{ mt: 2 }}>
            {validationResult.valid ? (
              <Alert severity="success">
                Valid {getDriveTypeLabel(validationResult.drive_type)} URL detected
              </Alert>
            ) : (
              <Alert severity="error">
                {validationResult.error_message}
              </Alert>
            )}
          </Box>
        )}
      </Box>

      {validationResult?.valid && (
        <FormControl fullWidth margin="normal">
          <InputLabel>Transfer Mode</InputLabel>
          <Select
            value={transferMode}
            onChange={(e) => setTransferMode(e.target.value as TransferMode)}
            label="Transfer Mode"
          >
            <MenuItem value={TransferMode.DIRECT_TO_NOTEBOOKLM}>
              Direct to NotebookLM (Faster)
            </MenuItem>
            <MenuItem value={TransferMode.VIA_GOOGLE_DRIVE}>
              Via Google Drive Landing Zone (Safer)
            </MenuItem>
          </Select>
        </FormControl>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
        <Button
          variant="outlined"
          onClick={onCancel}
          disabled={loading}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          variant="contained"
          disabled={!validationResult?.valid || loading}
        >
          {loading ? <CircularProgress size={20} /> : 'Start Transfer'}
        </Button>
      </Box>
    </Box>
  );
};

export default TransferForm;