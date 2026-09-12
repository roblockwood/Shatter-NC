import React, { createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useDemoWebSocket } from '../demo/useDemoWebSocket';
import type {
  MachineStatus,
  CompressorStatus,
  ProbeProgressCallback,
} from '../hooks/useWebSocket';
import { WS_URL } from '../config/api';
import { IS_DEMO_MODE } from '../config/demo';

interface WebSocketContextType {
  machines: MachineStatus[];
  compressors: CompressorStatus[];
  isConnected: boolean;
  removeMachine: (machineId: number) => void;
  addMachine: (machine: MachineStatus) => void;
  removeCompressor: (compressorId: number) => void;
  addCompressor: (compressor: CompressorStatus) => void;
  subscribeProbeProgress: (
    machineId: number,
    cb: ProbeProgressCallback
  ) => () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

const WebSocketContextProvider: React.FC<{ value: WebSocketContextType; children: ReactNode }> = ({
  value,
  children,
}) => <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;

const LiveWebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const value = useWebSocket(WS_URL);
  return <WebSocketContextProvider value={value}>{children}</WebSocketContextProvider>;
};

const DemoWebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const value = useDemoWebSocket();
  return <WebSocketContextProvider value={value}>{children}</WebSocketContextProvider>;
};

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) =>
  IS_DEMO_MODE ? (
    <DemoWebSocketProvider>{children}</DemoWebSocketProvider>
  ) : (
    <LiveWebSocketProvider>{children}</LiveWebSocketProvider>
  );

// eslint-disable-next-line react-refresh/only-export-components
export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};
