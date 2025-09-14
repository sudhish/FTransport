export interface Transfer {
  id: string;
  source_url: string;
  drive_type: DriveType;
  transfer_mode: TransferMode;
  status: TransferStatus;
  total_files: number;
  files_completed: number;
  current_file_name?: string;
  current_file_progress: number;
  overall_progress: number;
  landing_zone_folder_id?: string;
  notebooklm_notebook_id?: string;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export enum DriveType {
  GOOGLE_DRIVE = 'google_drive',
  ONEDRIVE = 'onedrive',
  DROPBOX = 'dropbox'
}

export enum TransferMode {
  DIRECT_TO_NOTEBOOKLM = 'direct_to_notebooklm',
  VIA_GOOGLE_DRIVE = 'via_google_drive'
}

export enum TransferStatus {
  PENDING = 'pending',
  SCANNING = 'scanning',
  TRANSFERRING = 'transferring',
  UPLOADING = 'uploading',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

export interface FileTransfer {
  file_name: string;
  file_size?: number;
  status: string;
  bytes_transferred: number;
  error_message?: string;
}

export interface TransferProgress {
  transfer_id: string;
  status: TransferStatus;
  stage: string;
  overall_progress: number;
  files_completed: number;
  total_files: number;
  current_file?: {
    name: string;
    progress: number;
    bytes_transferred?: number;
    total_bytes?: number;
  };
  file_details: Array<{
    name: string;
    status: string;
    size?: number;
    bytes_transferred?: number;
  }>;
  error_message?: string;
}

export interface CreateTransferRequest {
  source_url: string;
  transfer_mode?: TransferMode;
}

export interface URLValidationResponse {
  valid: boolean;
  drive_type?: DriveType;
  accessible: boolean;
  error_message?: string;
}