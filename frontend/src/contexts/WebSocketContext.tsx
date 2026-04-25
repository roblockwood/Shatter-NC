import React, { createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import type { MachineStatus, CompressorStatus } from '../hooks/useWebSocket';
import { WS_URL } from '../config/api';

interface WebSocketContextType {
  machines: MachineStatus[];
  compressors: CompressorStatus[];
  isConnected: boolean;
  removeMachine: (machineId: number) => void;
  addMachine: (machine: MachineStatus) => void;
  removeCompressor: (compressorId: number) => void;
  addCompressor: (compressor: CompressorStatus) => void;
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

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};

