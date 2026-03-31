import { useEffect, useRef, useState } from 'react';

export interface MachineStatus {
  machine_id: number;
  machine_name: string;
  is_online: boolean;
  status?: string;
  program_name?: string;
  mem_mode?: number;
  mem_operation_status?: number;
  cycle_time?: string;
  power_on_hours?: string;
  counters?: Array<{ counter_number: number; count: number }>;
  tools?: Array<{ tool_number: number; tool_name?: string; diameter?: number; length?: number; pot_number?: string | number }>;
  tool_table?: Array<{ tool_number: number; tool_name?: string; diameter?: number; length?: number; pot_number?: string | number }>;
  current_tool?: number;
  alarms?: Array<{
    code: string;
    message: string;
    description?: string;
    severity?: string;
    level_class?: string;
    stop_level?: string;
    reset_level?: string;
    cause?: string;
    solution?: string;
  }>;
  units?: 'in' | 'mm';
  error?: string;
  poll_timestamp: string;
  last_successful_poll_at?: string | null;
  tools_timestamp?: string | null;
  tool_table_timestamp?: string | null;
  macros_timestamp?: string | null;
  ip_address?: string;
  ftp_username?: string;
  ftp_password?: string;
  ftp_port?: number;
  http_port?: number;
  location?: string;
  poll_interval_seconds?: number;
  tool_poll_interval_seconds?: number;
  enabled?: boolean;
  part_display_mode?: 'cycle' | 'parts';
  layout_config?: Record<string, unknown> | null;
}

/** Kaeser compressor live status (kaeser-sc2-api sidecar + MQTT/REST) */
export interface CompressorStatus {
  asset_kind: 'compressor';
  compressor_id: number;
  compressor_name: string;
  ip_address: string;
  enabled?: boolean;
  sidecar_rest_base_url?: string;
  mqtt_topic_root?: string;
  kaeser_connect_base_url?: string | null;
  kaeser_username?: string | null;
  kaeser_credentials_configured?: boolean;
  poll_interval_seconds?: number;
  is_online: boolean;
  status?: string;
  alarms?: Array<{ code: string; message: string; severity?: string }>;
  metrics?: Record<string, unknown>;
  error?: string;
  poll_timestamp: string;
  last_successful_poll_at?: string | null;
  response_time_ms?: number;
  layout_config?: Record<string, unknown> | null;
}

interface WebSocketMessage {
  type: 'status_update' | 'initial_status' | 'compressor_status_update';
  timestamp: string;
  data?: MachineStatus | CompressorStatus;
  machines?: MachineStatus[];
  compressors?: CompressorStatus[];
}

export const useWebSocket = (url: string) => {
  const [machines, setMachines] = useState<Map<number, MachineStatus>>(new Map());
  const [compressors, setCompressors] = useState<Map<number, CompressorStatus>>(new Map());
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isConnectingRef = useRef(false);

  useEffect(() => {
    const connect = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN || isConnectingRef.current) {
        return;
      }

      try {
        isConnectingRef.current = true;
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          isConnectingRef.current = false;
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);

            if (message.type === 'initial_status' && message.machines) {
              const newMachines = new Map<number, MachineStatus>();
              message.machines.forEach((machine) => {
                newMachines.set(machine.machine_id, machine);
              });
              setMachines(newMachines);

              const newCompressors = new Map<number, CompressorStatus>();
              (message.compressors || []).forEach((c) => {
                newCompressors.set(c.compressor_id, c);
              });
              setCompressors(newCompressors);
            } else if (message.type === 'status_update' && message.data) {
              const d = message.data;
              if ('machine_id' in d && !('compressor_id' in d)) {
                const m = d as MachineStatus;
                setMachines((prev) => {
                  const updated = new Map(prev);
                  updated.set(m.machine_id, m);
                  return updated;
                });
              }
            } else if (message.type === 'compressor_status_update' && message.data && 'compressor_id' in message.data) {
              setCompressors((prev) => {
                const updated = new Map(prev);
                updated.set(
                  (message.data as CompressorStatus).compressor_id,
                  message.data as CompressorStatus
                );
                return updated;
              });
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onerror = () => {
          isConnectingRef.current = false;
        };

        ws.onclose = () => {
          setIsConnected(false);
          wsRef.current = null;
          isConnectingRef.current = false;

          reconnectTimeoutRef.current = window.setTimeout(() => {
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

  const removeCompressor = (compressorId: number) => {
    setCompressors((prev) => {
      const updated = new Map(prev);
      updated.delete(compressorId);
      return updated;
    });
  };

  const addCompressor = (c: CompressorStatus) => {
    setCompressors((prev) => {
      const updated = new Map(prev);
      updated.set(c.compressor_id, c);
      return updated;
    });
  };

  return {
    machines: Array.from(machines.values()),
    compressors: Array.from(compressors.values()),
    isConnected,
    removeMachine,
    addMachine,
    removeCompressor,
    addCompressor,
  };
};
