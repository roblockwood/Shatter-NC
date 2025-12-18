import React, { createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { WS_URL } from '../config/api';

interface WebSocketContextType {
  machines: any[];
  isConnected: boolean;
  removeMachine: (machineId: number) => void;
  addMachine: (machine: any) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { machines, isConnected, removeMachine, addMachine } = useWebSocket(WS_URL);

  return (
    <WebSocketContext.Provider value={{ machines, isConnected, removeMachine, addMachine }}>
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

