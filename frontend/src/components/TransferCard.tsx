import React from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  LinearProgress,
  Chip,
  Box
} from '@mui/material';
import { 
  CloudDone,
  Error,
  Pending,
  Sync,
  CloudUpload,
  Cancel
} from '@mui/icons-material';
import { Transfer, TransferStatus, DriveType } from '../types/index.ts';

interface TransferCardProps {
  transfer: Transfer;
  onClick: () => void;
}

const TransferCard: React.FC<TransferCardProps> = ({ transfer, onClick }) => {
  const getStatusIcon = (status: TransferStatus) => {
    switch (status) {
      case TransferStatus.COMPLETED:
        return <CloudDone color="success" />;
      case TransferStatus.FAILED:
        return <Error color="error" />;
      case TransferStatus.PENDING:
        return <Pending color="action" />;
      case TransferStatus.SCANNING:
      case TransferStatus.TRANSFERRING:
        return <Sync color="primary" className="rotating" />;
      case TransferStatus.UPLOADING:
        return <CloudUpload color="primary" />;
      case TransferStatus.CANCELLED:
        return <Cancel color="action" />;
      default:
        return <Pending color="action" />;
    }
  };

  const getStatusColor = (status: TransferStatus) => {
    switch (status) {
      case TransferStatus.COMPLETED:
        return 'success';
      case TransferStatus.FAILED:
        return 'error';
      case TransferStatus.CANCELLED:
        return 'default';
      default:
        return 'primary';
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Chip
            icon={getStatusIcon(transfer.status)}
            label={transfer.status.replace('_', ' ').toUpperCase()}
            color={getStatusColor(transfer.status) as any}
            variant="outlined"
          />
          <Typography variant="caption" color="text.secondary">
            {getDriveTypeLabel(transfer.drive_type)}
          </Typography>
        </Box>

        <Typography variant="h6" component="div" noWrap title={transfer.source_url}>
          {transfer.source_url.length > 50 
            ? `${transfer.source_url.substring(0, 47)}...` 
            : transfer.source_url
          }
        </Typography>

        <Typography variant="body2" color="text.secondary" gutterBottom>
          Created: {formatDate(transfer.created_at)}
        </Typography>

        {transfer.total_files > 0 && (
          <Box mt={2}>
            <Typography variant="body2" gutterBottom>
              Progress: {transfer.files_completed} / {transfer.total_files} files ({Math.round(transfer.overall_progress)}%)
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={transfer.overall_progress} 
              sx={{ mb: 1 }}
            />
          </Box>
        )}

        {transfer.current_file_name && (
          <Typography variant="caption" color="text.secondary">
            Current: {transfer.current_file_name}
          </Typography>
        )}

        {transfer.error_message && (
          <Typography variant="body2" color="error" sx={{ mt: 1 }}>
            Error: {transfer.error_message}
          </Typography>
        )}
      </CardContent>

      <CardActions>
        <Button size="small" onClick={onClick}>
          View Details
        </Button>
      </CardActions>
    </Card>
  );
};

export default TransferCard;