import React, { createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { WS_URL } from '../config/api';

interface WebSocketContextType {
  machines: any[];
  compressors: any[];
  isConnected: boolean;
  removeMachine: (machineId: number) => void;
  addMachine: (machine: any) => void;
  removeCompressor: (compressorId: number) => void;
  addCompressor: (compressor: any) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const {
    machines,
    compressors,
    isConnected,
    removeMachine,
    addMachine,
    removeCompressor,
    addCompressor,
  } = useWebSocket(WS_URL);

  return (
    <WebSocketContext.Provider
      value={{
        machines,
        compressors,
        isConnected,
        removeMachine,
        addMachine,
        removeCompressor,
        addCompressor,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

