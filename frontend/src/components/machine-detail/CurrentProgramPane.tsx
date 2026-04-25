import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE_URL } from '../../config/api';
import { earlierIsoTimestamp } from '../ui/pollingFreshness';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import './CurrentProgramPane.css';

interface ToolValidation {
  tool_number: number;
  required_diameter: number;
  required_length: number;
  available: boolean;
  diameter_match: boolean;
  length_sufficient: boolean;
  machine_tool_data: {
    tool_name?: string;
    diameter?: number;
    length?: number;
  };
  warnings: string[];
  validate_diameter?: boolean;
  validate_length?: boolean;
  requirements_complete?: boolean;
  tolerance_source?: 'machine_settings' | 'gcode_defaults';
  diameter_tolerance?: number;
  length_tolerance_plus?: number;
  length_tolerance_minus?: number;
}

interface WCSValidation {
  valid: boolean;
  work_offset: number;
  expected: {
    x: number;
    y: number;
    z: number;
  };
  actual: {
    x: number;
    y: number;
    z: number;
  };
  difference: {
    x: number;
    y: number;
    z: number;
  };
  tolerance: number;
  within_tolerance: boolean;
  warnings: string[];
}

interface Deployment {
  id: number;
  deployed_filename: string;
  deployed_at: string;
  deployed_path?: string;
  validation_passed?: boolean;
  program_id?: number;
  validation_results?: {
    tools?: { [key: number]: ToolValidation };
    wcs_offset?: WCSValidation | null;
    valid?: boolean;
  };
}

interface Program {
  id: number;
  original_filename: string;
  version_number: number;
  estimated_runtime_seconds?: number;
  program_metadata?: {
    tools?: Array<{ tool_number: number }>;
  };
}

interface CurrentProgramPaneProps {
  machineId: number;
  machineStatus?: string;
  programName?: string;  // Active program O-number from machine (e.g., "O2045")
  onExpand?: () => void;
  /** Last successful fast CNC poll (ISO). Combined with deployment API fetch time for the status light. */
  machineLastSuccessfulPollAt?: string | null;
}

interface FileInfo {
  name: string;
  size?: number;
  modified?: string;
}

// Module-level cache that persists across component unmounts
// Key: `${machineId}:${programName}`, Value: { deployment, program, fileInfo, timestamp }
const dataCache = new Map<string, {
  deployment: Deployment | null;
  program: Program | null;
  fileInfo: FileInfo | null;
  timestamp: number;
}>();

const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

function getCacheKey(machineId: number, programName?: string): string {
  return `${machineId}:${programName || 'none'}`;
}

function getCachedData(machineId: number, programName?: string): { deployment: Deployment | null; program: Program | null; fileInfo: FileInfo | null } | null {
  const key = getCacheKey(machineId, programName);
  const cached = dataCache.get(key);
  if (!cached) return null;
  
  // Check if cache is still valid
  const age = Date.now() - cached.timestamp;
  if (age > CACHE_TTL) {
    dataCache.delete(key);
    return null;
  }
  
  return {
    deployment: cached.deployment,
    program: cached.program,
    fileInfo: cached.fileInfo,
  };
}

function setCachedData(machineId: number, programName: string | undefined, deployment: Deployment | null, program: Program | null, fileInfo: FileInfo | null): void {
  const key = getCacheKey(machineId, programName);
  dataCache.set(key, {
    deployment,
    program,
    fileInfo,
    timestamp: Date.now(),
  });
}

function invalidateCache(machineId: number, programName?: string): void {
  const key = getCacheKey(machineId, programName);
  dataCache.delete(key);
}

export const CurrentProgramPane: React.FC<CurrentProgramPaneProps> = ({
  machineId,
  programName,
  onExpand,
  machineLastSuccessfulPollAt,
}) => {
  // Initialize state from cache if available (persists across unmounts)
  const cachedData = getCachedData(machineId, programName);
  const [deployment, setDeployment] = useState<Deployment | null>(cachedData?.deployment || null);
  const [program, setProgram] = useState<Program | null>(cachedData?.program || null);
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(cachedData?.fileInfo || null);
  
  // Initialize loading - false if we have cached data, true otherwise
  const [loading, setLoading] = useState(() => !cachedData);
  const [refreshing, setRefreshing] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false); // Track background refresh state
  const [refreshTrigger, setRefreshTrigger] = useState(0); // Force refresh when incremented
  const [lastFetchSuccessAt, setLastFetchSuccessAt] = useState<string | null>(null);
  const statusLightLastUpdatedAt = useMemo(
    () => earlierIsoTimestamp(lastFetchSuccessAt, machineLastSuccessfulPollAt),
    [lastFetchSuccessAt, machineLastSuccessfulPollAt],
  );
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());
  const [expandedWCS, setExpandedWCS] = useState<boolean>(false);
  const [liveValidation, setLiveValidation] = useState<Deployment['validation_results'] | null>(null);
  const [isRevalidating, setIsRevalidating] = useState(false);
  const hasAutoRevalidatedRef = useRef(false);
  const isInitialLoadRef = useRef(true);
  const previousMachineIdRef = useRef<number | null>(null);
  const previousProgramNameRef = useRef<string | undefined>(undefined);
  const hasDataRef = useRef(false);
  const lastFetchedProgramNameRef = useRef<string | undefined>(undefined); // Track which O-number we've already fetched

  useEffect(() => {
    // Check module-level cache first (persists across unmounts)
    // Skip cache if refreshTrigger was incremented (manual refresh)
    const cachedData = refreshTrigger > 0 ? null : getCachedData(machineId, programName);
    if (cachedData) {
      // We have cached data - restore it to state if not already there
      if (!deployment && !fileInfo) {
        setDeployment(cachedData.deployment);
        setProgram(cachedData.program);
        setFileInfo(cachedData.fileInfo);
      }
      setLoading(false);
      setIsRefreshing(false);
      previousMachineIdRef.current = machineId;
      previousProgramNameRef.current = programName;
      hasDataRef.current = true;
      lastFetchedProgramNameRef.current = programName;
      const key = getCacheKey(machineId, programName);
      const entry = dataCache.get(key);
      if (entry) {
        setLastFetchSuccessAt(new Date(entry.timestamp).toISOString());
      }
      
      // Cache hit - no logging needed
      return; // Skip fetching - we have cached data
    }
    
    // No cached data - proceed with fetch
    const isMachineChange = previousMachineIdRef.current !== null && previousMachineIdRef.current !== machineId;
    
    // Reset initial load flag only if machine changed
    if (isMachineChange) {
      isInitialLoadRef.current = true;
      hasDataRef.current = false;
      lastFetchedProgramNameRef.current = undefined;
    }
    
    const fetchCurrentDeployment = async () => {
      const recordFetchSuccess = () => setLastFetchSuccessAt(new Date().toISOString());
      const isNewProgramName = lastFetchedProgramNameRef.current !== programName;
      
      // Set loading/refreshing indicators
      if (isInitialLoadRef.current && !hasDataRef.current) {
        setLoading(true);
      } else if (hasDataRef.current && !isMachineChange && isNewProgramName) {
        setIsRefreshing(true);
      }
      
      // Update refs
      previousMachineIdRef.current = machineId;
      previousProgramNameRef.current = programName;
      
      try {
        // Fetch - if programName is available, use it; otherwise fall back to most recent
        // If we have program_name from machine status, fetch deployment by O-number
        // This ensures we show validation info for the ACTIVE program, not just the most recent deployment
        if (programName && programName !== '----' && programName !== 'undefined' && programName !== 'null' && programName.trim() !== '') {
          try {
            const response = await fetch(
              `${API_BASE_URL}/api/programs/machines/${machineId}/deployments/by-onumber/${encodeURIComponent(programName)}?include_program=true`
            );
            if (response.ok) {
              const data = await response.json();
              if (data.deployment) {
                const programData = data.program || null;
                setDeployment(data.deployment);
                setProgram(programData);
                setFileInfo(null); // Clear fileInfo when we have deployment data
                // Save to cache
                setCachedData(machineId, programName, data.deployment, programData, null);
                hasDataRef.current = true;
                lastFetchedProgramNameRef.current = programName; // Track that we've fetched this O-number
                if (isInitialLoadRef.current) {
                  isInitialLoadRef.current = false;
                  setLoading(false);
                }
                setIsRefreshing(false);
                setRefreshing(false);
                // Reset refreshTrigger after successful fetch so cache can be used next time
                if (refreshTrigger > 0) {
                  setRefreshTrigger(0);
                }
                recordFetchSuccess();
                return;
              } else {
                // No deployment found for this O-number - program may not be in database
                // This happens when a program is running directly on the machine without being deployed through the system
                setDeployment(null);
                setProgram(null);
              }
              
              // Try to fetch file info from machine (file size from file listing)
              if (programName) {
                try {
                  // Construct filename (e.g., "O2045" -> "O2045.NC")
                  const filename = programName.startsWith('O') ? `${programName}.NC` : `O${programName}.NC`;
                  
                  // List programs to find file size
                  const listResponse = await fetch(
                    `${API_BASE_URL}/api/machines/${machineId}/programs?path=/`
                  );
                  if (listResponse.ok) {
                    const listData = await listResponse.json();
                    const file = listData.programs?.find((p: { name: string; size?: number; modified?: string }) => 
                      p.name === filename || p.name === programName || p.name === `${programName}.NC`
                    );
                    const fileInfoData = file ? {
                      name: file.name || filename,
                      size: file.size,
                      modified: file.modified,
                    } : { name: filename };
                    
                    setFileInfo(fileInfoData);
                    // Save to cache
                    setCachedData(machineId, programName, null, null, fileInfoData);
                  } else {
                    // If listing fails, at least we have the programName
                    const fileInfoData = { name: filename };
                    setFileInfo(fileInfoData);
                    // Save to cache
                    setCachedData(machineId, programName, null, null, fileInfoData);
                  }
                } catch (err) {
                  // Silently handle errors
                  console.error('Error fetching file info:', err);
                  const filename = programName.startsWith('O') ? `${programName}.NC` : `O${programName}.NC`;
                  const fileInfoData = { name: filename };
                  setFileInfo(fileInfoData);
                  // Save to cache even on error (at least we have the filename)
                  setCachedData(machineId, programName, null, null, fileInfoData);
                }
                hasDataRef.current = true;
                lastFetchedProgramNameRef.current = programName; // Track that we've fetched this O-number
              }
              
              if (isInitialLoadRef.current) {
                isInitialLoadRef.current = false;
                setLoading(false);
              }
              setIsRefreshing(false);
              setRefreshing(false);
              // Reset refreshTrigger after fetch completes
              if (refreshTrigger > 0) {
                setRefreshTrigger(0);
              }
              recordFetchSuccess();
              return;
            }
            // If fetch failed but not 404, fall through to fallback
          } catch (err) {
            console.error('Error fetching deployment by O-number:', err);
            // Fall through to fallback
          }
        } else {
          // No valid programName — machine is idle or program is unknown.
          // Do NOT show the most recently deployed program; that would be misleading.
          setDeployment(null);
          setProgram(null);
          setFileInfo(null);
          hasDataRef.current = true;
          if (isInitialLoadRef.current) {
            isInitialLoadRef.current = false;
            setLoading(false);
          }
          setIsRefreshing(false);
          setRefreshing(false);
          if (refreshTrigger > 0) {
            setRefreshTrigger(0);
          }
          recordFetchSuccess();
          return;
        }
        
        // Fallback: programName was valid but the by-onumber fetch threw an exception.
        // Show the most recent deployment as a last resort so the pane is not empty.
        const response = await fetch(`${API_BASE_URL}/api/programs/machines/${machineId}/deployments?current_only=true`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            const deploymentData = data[0];
            let programData: Program | null = null;
            
            // Fetch program details if we have a program_id
            if (deploymentData.program_id) {
              try {
                const programResponse = await fetch(`${API_BASE_URL}/api/programs/${deploymentData.program_id}`);
                if (programResponse.ok) {
                  programData = await programResponse.json();
                }
              } catch (err) {
                console.error('Error fetching program details:', err);
              }
            }
            
            setDeployment(deploymentData);
            setProgram(programData);
            setFileInfo(null); // Clear fileInfo when we have deployment data
            // Save to cache
            setCachedData(machineId, programName, deploymentData, programData, null);
            hasDataRef.current = true;
            // Note: We don't set lastFetchedProgramNameRef here because this is a fallback
            // and we don't have a specific programName to track
            if (isInitialLoadRef.current) {
              isInitialLoadRef.current = false;
              setLoading(false);
            }
            setIsRefreshing(false);
            setRefreshing(false);
            recordFetchSuccess();
          } else {
            // No deployments found - if we have programName, try to fetch file info
            setDeployment(null);
            setProgram(null);
            
            if (programName && programName !== '----' && programName !== 'undefined' && programName !== 'null' && programName.trim() !== '') {
              // Try to fetch file info from machine
              try {
                const filename = programName.startsWith('O') ? `${programName}.NC` : `O${programName}.NC`;
                const listResponse = await fetch(
                  `${API_BASE_URL}/api/machines/${machineId}/programs?path=/`
                );
                if (listResponse.ok) {
                  const listData = await listResponse.json();
                  const file = listData.programs?.find((p: { name: string; size?: number; modified?: string }) => 
                    p.name === filename || p.name === programName || p.name === `${programName}.NC`
                  );
                  const fileInfoData = file ? {
                    name: file.name || filename,
                    size: file.size,
                    modified: file.modified,
                  } : { name: filename };
                  
                  setFileInfo(fileInfoData);
                  // Save to cache
                  setCachedData(machineId, programName, null, null, fileInfoData);
                  lastFetchedProgramNameRef.current = programName; // Track that we've fetched this O-number
                } else {
                  const fileInfoData = { name: filename };
                  setFileInfo(fileInfoData);
                  // Save to cache
                  setCachedData(machineId, programName, null, null, fileInfoData);
                }
                hasDataRef.current = true;
                if (!lastFetchedProgramNameRef.current) {
                  lastFetchedProgramNameRef.current = programName; // Track that we've fetched this O-number
                }
              } catch (err) {
                console.error('Error fetching file info in fallback:', err);
                const filename = programName.startsWith('O') ? `${programName}.NC` : `O${programName}.NC`;
                const fileInfoData = { name: filename };
                setFileInfo(fileInfoData);
                // Save to cache even on error
                setCachedData(machineId, programName, null, null, fileInfoData);
                hasDataRef.current = true;
                if (!lastFetchedProgramNameRef.current) {
                  lastFetchedProgramNameRef.current = programName; // Track that we've fetched this O-number
                }
              }
            }
            if (isInitialLoadRef.current) {
              isInitialLoadRef.current = false;
              setLoading(false);
            }
            setIsRefreshing(false);
            setRefreshing(false);
            recordFetchSuccess();
          }
        } else {
          // API call failed - if we have programName, at least show that
          setDeployment(null);
          setProgram(null);
          if (programName && programName !== '----' && programName !== 'undefined' && programName !== 'null' && programName.trim() !== '') {
            const filename = programName.startsWith('O') ? `${programName}.NC` : `O${programName}.NC`;
            const fileInfoData = { name: filename };
            setFileInfo(fileInfoData);
            // Save to cache
            setCachedData(machineId, programName, null, null, fileInfoData);
            hasDataRef.current = true;
            lastFetchedProgramNameRef.current = programName; // Track that we've fetched this O-number
          }
          if (isInitialLoadRef.current) {
            isInitialLoadRef.current = false;
            setLoading(false);
          }
          setIsRefreshing(false);
        }
      } catch (error) {
        console.error('Error fetching current deployment:', error);
        // Don't clear existing data on error
        if (isInitialLoadRef.current) {
          setDeployment(null);
          setProgram(null);
          isInitialLoadRef.current = false;
          setLoading(false);
        }
        setIsRefreshing(false);
        setRefreshing(false);
      } finally {
        // Reset refreshTrigger after fetch completes (success or error)
        // This allows cache to be used on subsequent loads
        if (refreshTrigger > 0) {
          setRefreshTrigger(0);
        }
      }
    };

      fetchCurrentDeployment();
  // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [machineId, programName, refreshTrigger]);

  const formatRuntime = (seconds?: number): string => {
    if (!seconds || seconds === 0) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const normalizeRemotePath = (rawPath?: string | null): string => {
    const normalized = `/${String(rawPath ?? '').replace(/\\/g, '/').split('/').filter(Boolean).join('/')}`;
    return normalized === '/' ? '/' : normalized;
  };

  const buildDeploymentFilePath = (dep: Deployment): string => {
    const filename = (dep.deployed_filename || '').trim();
    const rawPath = (dep.deployed_path || '').trim();

    if (!rawPath) {
      return normalizeRemotePath(filename ? `/${filename}` : '/');
    }

    const normalizedPath = normalizeRemotePath(rawPath);
    if (!filename) {
      return normalizedPath;
    }

    const pathLower = normalizedPath.toLowerCase();
    const fileLower = `/${filename.toLowerCase()}`;
    if (pathLower.endsWith(fileLower)) {
      return normalizedPath;
    }

    return normalizeRemotePath(`${normalizedPath}/${filename}`);
  };

  const buildFileBrowserLink = (fullFilePath: string): string => {
    const normalized = normalizeRemotePath(fullFilePath);
    const segments = normalized.split('/').filter(Boolean);
    const fileName = segments.length > 0 ? segments[segments.length - 1] : '';
    const directoryPath = segments.length > 1 ? `/${segments.slice(0, -1).join('/')}` : '/';

    return `/files?machine=${machineId}&file=${encodeURIComponent(fileName)}&file_path=${encodeURIComponent(normalized)}&path=${encodeURIComponent(directoryPath)}`;
  };

  const handleRevalidate = async (deploymentArg?: Deployment) => {
    const dep = deploymentArg || deployment;
    if (!dep) return;
    const filePath = buildDeploymentFilePath(dep);
    setIsRevalidating(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/programs/machines/${machineId}/programs/validate-file?file_path=${encodeURIComponent(filePath)}`,
        { method: 'POST' }
      );
      if (res.ok) {
        const data = await res.json();
        const freshValidation = {
          tools: data.validation?.tools ?? data.tools,
          wcs_offset: data.validation?.wcs_offset ?? data.wcs_offset ?? null,
          valid: data.validation?.valid ?? data.valid,
        };
        setLiveValidation(freshValidation);

        // Persist the fresh results back to the deployment record so that the
        // next page load shows current-machine-config tolerances, not the stale
        // upload-time results.
        if (dep.id) {
          try {
            await fetch(
              `${API_BASE_URL}/api/programs/deployments/${dep.id}/validation`,
              {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  validation_results: freshValidation,
                  validation_passed: freshValidation.valid ?? true,
                }),
              }
            );
            // Update the module-level cache so a cache-hit also shows fresh data
            if (programName) {
              const cached = dataCache.get(getCacheKey(machineId, programName));
              if (cached?.deployment) {
                cached.deployment.validation_results = freshValidation;
                cached.deployment.validation_passed = freshValidation.valid ?? true;
              }
            }
          } catch (patchErr) {
            // Persistence failure is non-fatal — live result is already shown
            console.warn('Could not persist re-validation results:', patchErr);
          }
        }
      }
    } catch (err) {
      console.error('Re-validate error:', err);
    } finally {
      setIsRevalidating(false);
    }
  };

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      setIsRefreshing(true);
      // Invalidate cache to force fresh fetch
      invalidateCache(machineId, programName);
      
      // Clear state to ensure we show fresh data
      setDeployment(null);
      setProgram(null);
      setFileInfo(null);
      hasDataRef.current = false;
      lastFetchedProgramNameRef.current = undefined;
      
      // Force a refetch by incrementing refreshTrigger
      // This will bypass cache and fetch fresh deployment data
      setRefreshTrigger(prev => prev + 1);
    } catch (error) {
      console.error('Error refreshing deployment data:', error);
      // On error, still invalidate cache and force refetch
      invalidateCache(machineId, programName);
      setRefreshTrigger(prev => prev + 1);
    }
    // Don't set refreshing to false here - let the fetch complete in useEffect
  };

  // Auto-revalidate when a deployment with failed tools is loaded for the first time
  useEffect(() => {
    if (!deployment || hasAutoRevalidatedRef.current) return;
    const tools = deployment.validation_results?.tools;
    if (!tools) return;
    const hasFailedTools = Object.values(tools).some(t => !t.available);
    if (hasFailedTools) {
      hasAutoRevalidatedRef.current = true;
      handleRevalidate(deployment);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deployment]);

  // Reset live validation only when the *program* actually changes, not on every render.
  // Using a ref to track the previous key avoids clearing liveValidation during the
  // periodic parent re-renders that pass the same machineId + programName, or during
  // brief poll cycles where programName momentarily becomes '----' then returns.
  const liveValidationKeyRef = useRef<string | null>(null);
  const currentKey = `${machineId}:${programName ?? ''}`;
  const isRealProgramName = programName && programName !== '----' && programName !== 'undefined' && programName !== 'null' && programName.trim() !== '';

  useEffect(() => {
    // Only treat this as a genuine program-change if the incoming name is a real O-number.
    // Ignore transient blank/placeholder values so a brief polling gap doesn't wipe the live result.
    if (!isRealProgramName) return;
    if (liveValidationKeyRef.current === currentKey) return;
    liveValidationKeyRef.current = currentKey;
    setLiveValidation(null);
    hasAutoRevalidatedRef.current = false;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentKey, isRealProgramName]);

  const extractONumber = (filename: string): string => {
    const match = filename.match(/O(\d{4})/i);
    return match ? match[1] : 'N/A';
  };

  const toggleToolExpanded = (toolNumber: number) => {
    setExpandedTools((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(toolNumber)) {
        newSet.delete(toolNumber);
      } else {
        newSet.add(toolNumber);
      }
      return newSet;
    });
  };

  const renderToolsValidationTable = () => {
    // Prefer live re-validation results; fall back to stored deployment results
    const validationResults = liveValidation ?? deployment?.validation_results;
    const isLiveResult = liveValidation !== null;
    // A "stale fail" is a stored result where a required tool (non-zero specs) shows not available
    const hasStaleFail = !isLiveResult && Object.values(deployment?.validation_results?.tools ?? {}).some(
      t => !t.available && (t.required_diameter !== 0 || t.required_length !== 0)
    );

    if (!validationResults?.tools) {
      return null;
    }

    const toolsArray = Object.values(validationResults.tools);
    const toleranceSource = toolsArray.find(t => t.tolerance_source)?.tolerance_source;

    if (toolsArray.length === 0) {
      return null;
    }

    return (
      <div className="validation-section">
        <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>TOOLS &amp; VALIDATION{hasStaleFail ? ' ⚠' : ''}</span>
          <button
            onClick={() => handleRevalidate()}
            disabled={isRevalidating}
            className="revalidate-btn"
            title="Re-run tool validation against current machine state"
          >
            {isRevalidating ? '[CHECKING...]' : '[RE-VALIDATE]'}
          </button>
        </div>
        {hasStaleFail && (
          <div style={{ fontSize: '0.7rem', color: '#ffcc80', padding: '2px 4px', marginBottom: '4px' }}>
            ⚠ Stored results may be stale — tool data was unavailable when deployed. Click RE-VALIDATE.
          </div>
        )}
        {toleranceSource && (
          <div style={{ fontSize: '0.7rem', color: '#9fb2c8', padding: '2px 4px', marginBottom: '4px' }}>
            Tolerance source: {toleranceSource === 'machine_settings' ? 'MACHINE SETTINGS' : 'PROGRAM DEFAULTS'}
          </div>
        )}
        <table className="validation-table">
          <thead>
            <tr className="validation-table-header">
              <th>ST</th>
              <th>TOOL#</th>
              <th>ACTUAL</th>
              <th>EXPECTED</th>
              <th>DIFF</th>
              <th>TOL</th>
              <th>RESULT</th>
            </tr>
          </thead>
          <tbody>
            {toolsArray.map((tool) => {
              const isExpanded = expandedTools.has(tool.tool_number);

              // Check if validation data is available
              const validationAvailable = tool.available !== undefined && tool.diameter_match !== undefined && tool.length_sufficient !== undefined;

              if (!validationAvailable) {
                // Tool was detected but not validated - show warning
                return (
                  <tr key={tool.tool_number} className="validation-table-row tool-summary-row">
                    <td className="text-warning">⚠</td>
                    <td>T{String(tool.tool_number).padStart(2, '0')}</td>
                    <td colSpan={4}>
                      <span className="text-warning">NOT CHECKED - Validation data unavailable</span>
                    </td>
                    <td className="text-warning">WARN</td>
                  </tr>
                );
              }
              
              const requirementsMissing = tool.requirements_complete === false;

              // Check if tool is not referenced in NC (required values are 0)
              const notInNC = !requirementsMissing && tool.required_diameter === 0 && tool.required_length === 0;
              
              if (notInNC) {
                // Tool is available on machine but not referenced in NC program
                return (
                  <tr key={tool.tool_number} className="validation-table-row tool-summary-row">
                    <td className="text-muted">─</td>
                    <td>T{String(tool.tool_number).padStart(2, '0')}</td>
                    <td>
                      Ø{(tool.machine_tool_data.diameter || 0).toFixed(3)}" L{(tool.machine_tool_data.length || 0).toFixed(4)}"
                      {tool.machine_tool_data.tool_name && (
                        <span className="text-muted"> ({tool.machine_tool_data.tool_name})</span>
                      )}
                    </td>
                    <td className="text-muted">────</td>
                    <td className="text-muted">────</td>
                    <td className="text-muted">─</td>
                    <td className="text-muted">N/A</td>
                  </tr>
                );
              }

              // Determine overall status
              const toolPassed = tool.available && tool.diameter_match && tool.length_sufficient;
              const hasError = !tool.available || ((tool.validate_length ?? true) && !tool.length_sufficient);
              const hasWarning = requirementsMissing || (tool.available && (tool.validate_diameter ?? true) && !tool.diameter_match);
              const statusClass = hasError ? 'text-error' : hasWarning ? 'text-warning' : 'text-success';
              const statusIcon = hasError ? '✕' : hasWarning ? '⚠' : '✓';
              const expandIcon = isExpanded ? '▼' : '▶';

              // Calculate values for length and diameter
              const actualLength = tool.machine_tool_data.length || 0;
              const requiredLength = tool.required_length;
              const lengthDiff = actualLength - requiredLength;
              const lengthPassed = tool.length_sufficient;

              const actualDiameter = tool.machine_tool_data.diameter || 0;
              const requiredDiameter = tool.required_diameter;
              const diameterDiff = actualDiameter - requiredDiameter;
              const diameterPassed = tool.diameter_match;

              return (
                <React.Fragment key={tool.tool_number}>
                  {/* Summary Row */}
                  <tr
                    className="validation-table-row tool-summary-row"
                    onClick={() => tool.available && toggleToolExpanded(tool.tool_number)}
                    style={{ cursor: tool.available ? 'pointer' : 'default' }}
                  >
                    <td className={statusClass}>{statusIcon}</td>
                    <td>
                      {tool.available && <span className="expand-icon">{expandIcon}</span>}
                      T{String(tool.tool_number).padStart(2, '0')}
                    </td>
                    <td colSpan={4}>
                      {!tool.available ? (
                        <span className="text-error">NOT AVAILABLE</span>
                      ) : requirementsMissing ? (
                        <span className="text-warning">TOOL CALL FOUND - HEADER DIAMETER/LENGTH NOT PROVIDED</span>
                      ) : (
                        <>
                          {tool.machine_tool_data.tool_name && (
                            <span className="text-muted">{tool.machine_tool_data.tool_name}</span>
                          )}
                        </>
                      )}
                    </td>
                    <td className={statusClass}>
                      {toolPassed ? 'PASS' : 'FAIL'}
                    </td>
                  </tr>

                  {/* Detail Rows - Length */}
                  {isExpanded && tool.available && (
                    <tr className="validation-table-row tool-detail-row">
                      <td></td>
                      <td className="detail-label">Length</td>
                      <td>{actualLength.toFixed(4)}"</td>
                      <td>{requiredLength.toFixed(4)}"</td>
                      <td className={lengthPassed ? 'text-success' : 'text-error'}>
                        {lengthDiff.toFixed(4)}"
                      </td>
                      <td>
                        {tool.length_tolerance_plus != null && tool.length_tolerance_minus != null
                          ? `+${tool.length_tolerance_plus.toFixed(4)}"/-${tool.length_tolerance_minus.toFixed(4)}"`
                          : ((tool.validate_length ?? true) ? '≥ required' : 'SKIPPED')}
                      </td>
                      <td className={lengthPassed ? 'text-success' : 'text-error'}>
                        {(tool.validate_length ?? true) ? (lengthPassed ? '✓' : '✕') : '─'}
                      </td>
                    </tr>
                  )}

                  {/* Detail Rows - Diameter */}
                  {isExpanded && tool.available && (
                    <tr className="validation-table-row tool-detail-row">
                      <td></td>
                      <td className="detail-label">Diameter</td>
                      <td>{actualDiameter.toFixed(3)}"</td>
                      <td>{requiredDiameter.toFixed(3)}"</td>
                      <td className={diameterPassed ? 'text-success' : 'text-error'}>
                        {diameterDiff.toFixed(3)}"
                      </td>
                      <td>
                        {tool.diameter_tolerance != null
                          ? `±${tool.diameter_tolerance.toFixed(4)}"`
                          : ((tool.validate_diameter ?? true) ? 'exact match' : 'SKIPPED')}
                      </td>
                      <td className={diameterPassed ? 'text-success' : 'text-error'}>
                        {(tool.validate_diameter ?? true) ? (diameterPassed ? '✓' : '✕') : '─'}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  const renderWCSSection = () => {
    const wcsData = deployment?.validation_results?.wcs_offset;

    // Always show WCS section, even if data wasn't included
    if (!wcsData) {
      return (
        <div className="validation-section">
          <div className="section-header">WCS OFFSET</div>
          <table className="validation-table">
            <thead>
              <tr className="validation-table-header">
                <th>ST</th>
                <th>OFFSET</th>
                <th>ACTUAL</th>
                <th>EXPECTED</th>
                <th>DIFF</th>
                <th>TOL</th>
                <th>RESULT</th>
              </tr>
            </thead>
            <tbody>
              <tr className="validation-table-row wcs-summary-row">
                <td className="text-muted">─</td>
                <td>N/A</td>
                <td colSpan={4} className="text-muted">
                  NO WCS DATA AVAILABLE
                </td>
                <td className="text-muted">N/A</td>
              </tr>
            </tbody>
          </table>
        </div>
      );
    }

    // Check if WCS was not specified in NC (expected values are all 0)
    const notInNC = wcsData.expected.x === 0 && 
                    wcsData.expected.y === 0 && 
                    wcsData.expected.z === 0 &&
                    wcsData.warnings?.some(w => w.includes("not specified in NC"));

    if (notInNC) {
      // WCS not specified in NC - show collapsed summary with machine data
      const expandIcon = expandedWCS ? '▼' : '▶';
      
      return (
        <div className="validation-section">
          <div className="section-header">WCS OFFSET</div>
          <table className="validation-table">
            <thead>
              <tr className="validation-table-header">
                <th>ST</th>
                <th>OFFSET</th>
                <th>ACTUAL</th>
                <th>EXPECTED</th>
                <th>DIFF</th>
                <th>TOL</th>
                <th>RESULT</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                className="validation-table-row wcs-summary-row"
                onClick={() => setExpandedWCS(!expandedWCS)}
                style={{ cursor: 'pointer' }}
              >
                <td className="text-warning">⚠</td>
                <td>
                  <span className="expand-icon">{expandIcon}</span>
                  G{wcsData.work_offset}
                </td>
                <td colSpan={4} className="text-muted">
                  XYZ NOT PARSED
                </td>
                <td className="text-warning">WARN</td>
              </tr>

              {expandedWCS && wcsData && ['x', 'y', 'z'].map((axis) => {
                const actual = wcsData.actual[axis as keyof typeof wcsData.actual];
                return (
                  <tr key={axis} className="validation-table-row wcs-detail-row">
                    <td></td>
                    <td className="detail-label">{axis.toUpperCase()}</td>
                    <td>{actual.toFixed(4)}"</td>
                    <td className="text-muted">────</td>
                    <td className="text-muted">────</td>
                    <td className="text-muted">─</td>
                    <td className="text-muted">N/A</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      );
    }

    // Check if validation data is available
    const validationAvailable = wcsData.within_tolerance !== undefined &&
                                 wcsData.actual !== undefined &&
                                 wcsData.expected !== undefined;

    if (!validationAvailable) {
      // WCS was detected but not validated - show warning
      return (
        <div className="validation-section">
          <div className="section-header">WCS OFFSET</div>
          <table className="validation-table">
            <thead>
              <tr className="validation-table-header">
                <th>ST</th>
                <th>OFFSET</th>
                <th>ACTUAL</th>
                <th>EXPECTED</th>
                <th>DIFF</th>
                <th>TOL</th>
                <th>RESULT</th>
              </tr>
            </thead>
            <tbody>
              <tr className="validation-table-row wcs-summary-row">
                <td className="text-warning">⚠</td>
                <td>G{wcsData.work_offset}</td>
                <td colSpan={4}>
                  <span className="text-warning">NOT CHECKED - Validation data unavailable</span>
                </td>
                <td className="text-warning">WARN</td>
              </tr>
            </tbody>
          </table>
        </div>
      );
    }

    const tolerance = wcsData.tolerance;
    const withinTolerance = wcsData.within_tolerance;
    const statusClass = withinTolerance ? 'text-success' : 'text-error';
    const statusIcon = withinTolerance ? '✓' : '✕';
    const expandIcon = expandedWCS ? '▼' : '▶';

    return (
      <div className="validation-section">
        <div className="section-header">WCS OFFSET</div>
        <table className="validation-table">
          <thead>
            <tr className="validation-table-header">
              <th>ST</th>
              <th>OFFSET</th>
              <th>ACTUAL</th>
              <th>EXPECTED</th>
              <th>DIFF</th>
              <th>TOL</th>
              <th>RESULT</th>
            </tr>
          </thead>
          <tbody>
            {/* Summary Row */}
            <tr
              className="validation-table-row wcs-summary-row"
              onClick={() => setExpandedWCS(!expandedWCS)}
              style={{ cursor: 'pointer' }}
            >
              <td className={statusClass}>{statusIcon}</td>
              <td>
                <span className="expand-icon">{expandIcon}</span>
                G{wcsData.work_offset}
              </td>
              <td colSpan={4}>
                <span className="text-muted">X/Y/Z Coordinates</span>
              </td>
              <td className={statusClass}>
                {withinTolerance ? 'PASS' : 'FAIL'}
              </td>
            </tr>

            {/* Detail Rows - X/Y/Z Axes */}
            {expandedWCS && ['x', 'y', 'z'].map((axis) => {
              const actual = wcsData.actual[axis as keyof typeof wcsData.actual];
              const expected = wcsData.expected[axis as keyof typeof wcsData.expected];
              const diff = wcsData.difference[axis as keyof typeof wcsData.difference];
              const absDiff = Math.abs(diff);
              const axisWithinTol = absDiff <= tolerance;
              const axisStatusClass = axisWithinTol ? 'text-success' : 'text-error';
              const axisStatusIcon = axisWithinTol ? '✓' : '✕';

              return (
                <tr key={axis} className="validation-table-row wcs-detail-row">
                  <td></td>
                  <td className="detail-label">{axis.toUpperCase()}</td>
                  <td>{actual.toFixed(4)}"</td>
                  <td>{expected.toFixed(4)}"</td>
                  <td className={axisStatusClass}>{diff.toFixed(4)}"</td>
                  <td>±{tolerance.toFixed(4)}"</td>
                  <td className={axisStatusClass}>{axisStatusIcon}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div 
      className="current-program-pane terminal-box"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>┌─ CURRENT PROGRAM {'─'.repeat(25)}</span>
            {isRefreshing && (
              <span className="refresh-indicator" style={{ marginLeft: '8px', color: '#888', fontSize: '12px' }} title="Refreshing data...">
                ⟳
              </span>
            )}
            <div className="pane-header-right-actions">
              <PollingStatusLight
                lastUpdatedAt={statusLightLastUpdatedAt}
                expectedIntervalMs={300_000}
                ariaLabel="Current program pane data freshness"
              />
              <button 
                className="expand-toggle"
                onClick={(e) => {
                  e.stopPropagation();
                  handleRefresh();
                }}
                disabled={refreshing}
                title="Refresh deployment data"
              >
                {refreshing ? '[...]' : '[REFRESH]'}
              </button>
              {onExpand && (
                <button 
                  className="expand-toggle"
                  onClick={(e) => {
                    e.stopPropagation();
                    onExpand();
                  }}
                  title="Expand"
                >
                  [EXPAND]
                </button>
              )}
              <span>┐</span>
            </div>
          </div>
        </div>
      </div>
      <div className="terminal-box-content">
        {loading && !isRefreshing && !deployment && !fileInfo ? (
          <div className="program-loading">LOADING...</div>
        ) : !deployment && !programName ? (
          <div className="program-empty">NO PROGRAM DEPLOYED</div>
        ) : !deployment && programName ? (
          // Show program info even when there's no deployment data
          <div className="program-info">
            <div className="program-row">
              <span className="program-label">O-NUMBER:</span>
              <span className="program-value text-info">{programName}</span>
            </div>
            {fileInfo && (
              <>
                <div className="program-row">
                  <span className="program-label">FILENAME:</span>
                  <span className="program-value">
                    <Link 
                      to={`/files?machine=${machineId}&file=${encodeURIComponent(fileInfo.name)}`}
                      className="program-filename-link"
                    >
                      {fileInfo.name}
                    </Link>
                  </span>
                </div>
                {fileInfo.size !== undefined && (
                  <div className="program-row">
                    <span className="program-label">SIZE:</span>
                    <span className="program-value">{formatFileSize(fileInfo.size)}</span>
                  </div>
                )}
                {fileInfo.modified && (
                  <div className="program-row">
                    <span className="program-label">MODIFIED:</span>
                    <span className="program-value">
                      {new Date(fileInfo.modified).toLocaleString()}
                    </span>
                  </div>
                )}
              </>
            )}
            <div className="program-row">
              <span className="program-label">STATUS:</span>
              <span className="program-value text-warning">NO DEPLOYMENT DATA</span>
            </div>
          </div>
        ) : (
          <>
            <div className="program-info">
              <div className="program-row">
                <span className="program-label">O-NUMBER:</span>
                <span className="program-value text-info">{extractONumber(deployment!.deployed_filename)}</span>
              </div>
              <div className="program-row">
                <span className="program-label">FILENAME:</span>
                <span className="program-value">
                  <Link
                    to={buildFileBrowserLink(buildDeploymentFilePath(deployment!))}
                    className="program-filename-link"
                    title={`Open in File Browser: ${buildDeploymentFilePath(deployment!)}`}
                  >
                    {deployment!.deployed_filename}
                  </Link>
                </span>
              </div>
              <div className="program-row">
                <span className="program-label">FILE PATH:</span>
                <span className="program-value">{buildDeploymentFilePath(deployment!)}</span>
              </div>
              {program && (
                <>
                  <div className="program-row">
                    <span className="program-label">ORIGINAL:</span>
                    <span className="program-value">{program.original_filename}</span>
                  </div>
                  {program.version_number > 1 && (
                    <div className="program-row">
                      <span className="program-label">VERSION:</span>
                      <span className="program-value">v{program.version_number}</span>
                    </div>
                  )}
                  {program.estimated_runtime_seconds && (
                    <div className="program-row">
                      <span className="program-label">RUNTIME:</span>
                      <span className="program-value">{formatRuntime(program.estimated_runtime_seconds)}</span>
                    </div>
                  )}
                </>
              )}
              <div className="program-row">
                <span className="program-label">DEPLOYED:</span>
                <span className="program-value">
                  {new Date(deployment!.deployed_at).toLocaleString()}
                </span>
              </div>
              {deployment!.validation_passed !== undefined && (
                <div className="program-row">
                  <span className="program-label">VALIDATION:</span>
                  <span className={`program-value ${deployment!.validation_passed !== false ? 'text-success' : 'text-error'}`}>
                    {deployment!.validation_passed !== false ? 'PASSED ✓' : 'FAILED ✕'}
                  </span>
                </div>
              )}
            </div>
            {renderToolsValidationTable()}
            {renderWCSSection()}
          </>
        )}
      </div>
      <div className="terminal-box-footer">
        └{'─'.repeat(42)}┘
      </div>
    </div>
  );
};

