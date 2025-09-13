import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { Transfer } from '../types/index.ts';

interface TransferState {
  transfers: Transfer[];
  activeTransfer: Transfer | null;
  loading: boolean;
  error: string | null;
}

type TransferAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_TRANSFERS'; payload: Transfer[] }
  | { type: 'ADD_TRANSFER'; payload: Transfer }
  | { type: 'UPDATE_TRANSFER'; payload: Transfer }
  | { type: 'SET_ACTIVE_TRANSFER'; payload: Transfer | null };

const initialState: TransferState = {
  transfers: [],
  activeTransfer: null,
  loading: false,
  error: null,
};

const transferReducer = (state: TransferState, action: TransferAction): TransferState => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_TRANSFERS':
      return { ...state, transfers: action.payload };
    case 'ADD_TRANSFER':
      return { ...state, transfers: [...state.transfers, action.payload] };
    case 'UPDATE_TRANSFER':
      const updatedTransfers = state.transfers.map(transfer =>
        transfer.id === action.payload.id ? action.payload : transfer
      );
      return {
        ...state,
        transfers: updatedTransfers,
        activeTransfer: state.activeTransfer?.id === action.payload.id ? action.payload : state.activeTransfer
      };
    case 'SET_ACTIVE_TRANSFER':
      return { ...state, activeTransfer: action.payload };
    default:
      return state;
  }
};

const TransferContext = createContext<{
  state: TransferState;
  dispatch: React.Dispatch<TransferAction>;
} | null>(null);

export const TransferProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(transferReducer, initialState);

  return (
    <TransferContext.Provider value={{ state, dispatch }}>
      {children}
    </TransferContext.Provider>
  );
};

export const useTransfer = () => {
  const context = useContext(TransferContext);
  if (!context) {
    throw new Error('useTransfer must be used within a TransferProvider');
  }
  return context;
};