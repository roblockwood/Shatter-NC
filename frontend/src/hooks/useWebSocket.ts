import { useEffect, useRef, useState } from 'react';

interface MachineStatus {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  status?: string;
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

  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('WebSocket connected');
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);

            if (message.type === 'initial_status' && message.machines) {
              // Initial status - update all machines
              const newMachines = new Map<number, MachineStatus>();
              message.machines.forEach((machine) => {
                newMachines.set(machine.machine_id, machine);
              });
              setMachines(newMachines);
            } else if (message.type === 'status_update' && message.data) {
              // Update single machine
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
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setIsConnected(false);
          wsRef.current = null;

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

  return {
    machines: Array.from(machines.values()),
    isConnected,
  };
};
