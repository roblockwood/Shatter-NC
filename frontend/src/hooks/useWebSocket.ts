import { useEffect, useRef, useState } from 'react';

interface MachineStatus {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  status?: string;
  program_name?: string;  // Active program O-number from machine (e.g., "O2045")
  cycle_time?: string;
  power_on_hours?: string;
  counters?: Array<{ counter_number: number; count: number }>;
  error?: string;
  poll_timestamp: string;
  ip_address?: string;
  ftp_username?: string;
  ftp_password?: string;
  ftp_port?: number;
  http_port?: number;
  location?: string;
  poll_interval_seconds?: number;
  enabled?: boolean;
  tools?: Array<{ tool_number: number; tool_name?: string; diameter?: number; length?: number }>;
  current_tool?: number;
  alarms?: Array<{ code: string; message: string }>;
}

interface WebSocketMessage {
  type: 'status_update' | 'initial_status';
  timestamp: string;
  data?: MachineStatus;
  machines?: MachineStatus[];
}

export const useWebSocket = (url: string) => {
  const [machines, setMachines] = useState<Map<number, MachineStatus>>(new Map());
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isConnectingRef = useRef(false);

  useEffect(() => {
    const connect = () => {
      // Prevent duplicate connections
      if (wsRef.current?.readyState === WebSocket.OPEN || isConnectingRef.current) {
        return;
      }
      
      try {
        isConnectingRef.current = true;
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('WebSocket connected');
          setIsConnected(true);
          isConnectingRef.current = false;
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);

            if (message.type === 'initial_status' && message.machines) {
              // Initial status - update all machines
              const newMachines = new Map<number, MachineStatus>();
              message.machines.forEach((machine) => {
                // Reduced logging - only log on initial connection
                // console.log(`[WebSocket] Initial status for machine ${machine.machine_id}:`, { program_name: machine.program_name, status: machine.status });
                newMachines.set(machine.machine_id, machine);
              });
              setMachines(newMachines);
            } else if (message.type === 'status_update' && message.data) {
              // Update single machine
              // Reduced logging - uncomment if needed for debugging
              // console.log(`[WebSocket] Status update for machine ${message.data.machine_id}:`, { program_name: message.data.program_name, status: message.data.status });
              setMachines((prev) => {
                const updated = new Map(prev);
                updated.set(message.data!.machine_id, message.data!);
                return updated;
              });
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          isConnectingRef.current = false;
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setIsConnected(false);
          wsRef.current = null;
          isConnectingRef.current = false;

          // Attempt to reconnect after 5 seconds
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log('Attempting to reconnect...');
            connect();
          }, 5000);
        };
      } catch (error) {
        console.error('Error connecting to WebSocket:', error);
      }
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  const removeMachine = (machineId: number) => {
    setMachines((prev) => {
      const updated = new Map(prev);
      updated.delete(machineId);
      return updated;
    });
  };

  const addMachine = (machine: MachineStatus) => {
    setMachines((prev) => {
      const updated = new Map(prev);
      updated.set(machine.machine_id, machine);
      return updated;
    });
  };

  return {
    machines: Array.from(machines.values()),
    isConnected,
    removeMachine,
    addMachine,
  };
};
