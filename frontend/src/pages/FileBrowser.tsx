import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { StatusIndicator } from '../components/ui';
import './FileBrowser.css';
import { API_BASE_URL } from '../config/api';

interface Program {
  name: string;
  size: number;
  modified: string;
  is_directory: boolean;
  path: string;
}

interface Machine {
  id: number;
  name: string;
  ip_address: string;
  path?: string;
}

interface ViewData {
  file_path: string;
  content: string;
  size: number;
  lines: number;
}

interface FileMetadata {
  file_path: string;
  tools: number[];
  runtime_seconds: number;
  has_errors: boolean;
}

interface ToolDetail {
  tool_number: number;
  diameter: number;
  corner_radius: number;
  description: string;
  length_total: number;
}

interface ToolValidation {
  tool_number: number;
  required_diameter: number;
  required_length: number;
  available: boolean;
  diameter_match: boolean;
  length_sufficient: boolean;
  machine_tool_data: any;
  warnings: string[];
}

interface WCSValidation {
  valid: boolean;
  work_offset: number;
  expected: { x: number; y: number; z: number };
  actual: { x: number; y: number; z: number };
  difference: { x: number; y: number; z: number };
  tolerance: number;
  within_tolerance: boolean;
  warnings: string[];
}

interface ValidationResults {
  valid: boolean;
  tools: { [key: number]: ToolValidation };
  wcs_offset?: WCSValidation;
  warnings: string[];
  errors: string[];
}

interface FreshValidationState {
  validation: ValidationResults;
  gcode_content: string;
  timestamp: number;
}

interface DeploymentHistoryEntry {
  id: number;
  deployed_at: string;
  validation_passed: boolean | null;
  replaced_at: string | null;
  is_current: boolean;
  program_version: number | null;
  original_filename: string | null;
}

interface DeploymentDetail {
  deployment: {
    id: number;
    deployed_filename: string;
    deployed_path: string;
    deployed_at: string;
    validation_passed: boolean | null;
    validation_results: ValidationResults | null;
  };
  program: {
    id: number;
    original_filename: string;
    version_number: number;
    posted_date: string | null;
    estimated_runtime_seconds: number;
    program_metadata: {
      tools: ToolDetail[];
      wcs_offset?: any;
      stock_size?: any;
    };
    file_size_bytes: number;
    line_count: number;
  } | null;
  history?: DeploymentHistoryEntry[];
}

export const FileBrowser: React.FC = () => {
  const [searchParams] = useSearchParams();
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const deploymentSectionRef = React.useRef<HTMLDivElement>(null);
  const selectedProgramRef = React.useRef<HTMLDivElement>(null);
  const [machines, setMachines] = useState<Machine[]>([]);
  const [selectedMachineId, setSelectedMachineId] = useState<number | null>(null);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [selectedProgram, setSelectedProgram] = useState<Program | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPath, setCurrentPath] = useState<string | null>(null);
  const [pathLoading, setPathLoading] = useState(false);
  const [previewLines, setPreviewLines] = useState<string[]>([]);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [viewModalContent, setViewModalContent] = useState<ViewData | null>(null);
  const [viewModalLoading, setViewModalLoading] = useState(false);
  // @ts-ignore - reserved for future use
  const [fileMetadata, setFileMetadata] = useState<FileMetadata | null>(null);
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [deploymentDetail, setDeploymentDetail] = useState<DeploymentDetail | null>(null);
  const [deploymentLoading, setDeploymentLoading] = useState(false);
  const [deploymentError, setDeploymentError] = useState<string | null>(null);
  const [selectedDeploymentId, setSelectedDeploymentId] = useState<number | null>(null);
  const [freshValidation, setFreshValidation] = useState<FreshValidationState | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<{ fileName: string; percent: number } | null>(null);
  // @ts-ignore - reserved for future use
  const [highlightedFile, setHighlightedFile] = useState<string | null>(null);
  const [pendingFileSelection, setPendingFileSelection] = useState<string | null>(null);
  // Expand/collapse state for validation tables
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());
  const [expandedWCS, setExpandedWCS] = useState(false);

  // Fetch machines on mount and auto-select first one
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/machines`)
      .then(res => res.json())
      .then(data => {
        setMachines(data);
        // Auto-select first machine, path effect will handle loading the correct path
        if (data.length > 0) {
          setSelectedMachineId(data[0].id);
        }
      })
      .catch(err => console.error('Error fetching machines:', err));
  }, []);

  // Handle URL parameters for navigation from upload success screen
  useEffect(() => {
    const machineParam = searchParams.get('machine');
    const fileParam = searchParams.get('file');

    if (machineParam && fileParam && machines.length > 0) {
      const machineId = parseInt(machineParam);

      // Set selected machine if different
      if (!isNaN(machineId) && selectedMachineId !== machineId) {
        setSelectedMachineId(machineId);
      }

      // Store pending file selection - will be handled once programs load
      setPendingFileSelection(fileParam);
    }
  }, [searchParams, machines.length, selectedMachineId]);

  // Handle pending file selection once programs are loaded
  useEffect(() => {
    if (pendingFileSelection && programs.length > 0 && !loading) {
      // Case-insensitive file matching (CNC may return uppercase .NC)
      const targetProgram = programs.find(p => p.name.toUpperCase() === pendingFileSelection.toUpperCase());

      if (targetProgram) {
        setSelectedProgram(targetProgram);
        setPendingFileSelection(null); // Clear pending selection

        // Scroll to selected program in list and then to deployment section
        setTimeout(() => {
          // First scroll the program into view in the programs list
          selectedProgramRef.current?.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
          });

          // Then scroll to deployment section if it's an O-number file
          setTimeout(() => {
            deploymentSectionRef.current?.scrollIntoView({
              behavior: 'smooth',
              block: 'start'
            });
          }, 300);
        }, 100);
      }
    }
  }, [pendingFileSelection, programs.length, loading]);

  // Set path when machine changes - fetch fresh machine data to ensure we have latest config
  useEffect(() => {
    if (selectedMachineId === null) return;

    // Immediately clear path and set loading before any async operations
    setPathLoading(true);
    setCurrentPath(null);

    // Fetch fresh machine data to ensure we have the latest path configuration
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/api/machines/${selectedMachineId}`, {
      signal: controller.signal,
    })
      .then(res => res.json())
      .then(machineData => {
        const newPath = machineData.path || '/';
        setCurrentPath(newPath);
        setPathLoading(false);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error(`Error fetching machine ${selectedMachineId}:`, err);
          setCurrentPath('/');
          setPathLoading(false);
        }
      });

    return () => controller.abort();
  }, [selectedMachineId]);

  // Fetch programs when machine or path changes
  useEffect(() => {
    // Don't fetch if path is null OR if we're still loading the path
    if (selectedMachineId === null || currentPath === null || pathLoading) {
      return;
    }

    // Check cache first for instant loading
    const cacheKey = `programs_cache_${selectedMachineId}_${currentPath}`;
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) {
      try {
        const cacheData = JSON.parse(cached);
        const age = Date.now() - cacheData.timestamp;
        // Use cache if less than 60 seconds old
        if (age < 60000 && cacheData.machineId === selectedMachineId && cacheData.path === currentPath) {
          setPrograms(cacheData.programs);
          setLoading(false);
          setError(null);
          setSelectedProgram(null);
          return;
        } else {
          sessionStorage.removeItem(cacheKey);
        }
      } catch (e) {
        sessionStorage.removeItem(cacheKey);
      }
    }

    setLoading(true);
    setError(null);
    setPrograms([]);
    setSelectedProgram(null);

    const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/programs?path=${encodeURIComponent(currentPath)}`;

    const controller = new AbortController();
    const fetchMachineId = selectedMachineId;
    const fetchPath = currentPath;

    fetch(url, { signal: controller.signal })
      .then(res => {
        if (!res.ok) {
          return res.json().then(data => {
            throw new Error(data.detail || `HTTP ${res.status}`);
          }).catch(() => {
            throw new Error(`HTTP ${res.status}`);
          });
        }
        return res.json();
      })
      .then(data => {
        // Only update if this fetch is still relevant (machine and path haven't changed)
        if (fetchMachineId === selectedMachineId && fetchPath === currentPath) {
          setPrograms(data.programs || []);
          setLoading(false);
        }
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching programs:', err);
          const errorMsg = err.message || 'Unknown error';
          if (errorMsg.includes('timeout')) {
            setError('FTP connection timeout - check machine network connectivity');
          } else if (errorMsg.includes('ConnectionReset') || errorMsg === '') {
            setError('FTP server connection refused - verify machine FTP service is running');
          } else {
            setError(`Error: ${errorMsg}`);
          }
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [selectedMachineId, currentPath, pathLoading]);

  // Fetch preview and metadata when a .nc file is selected
  useEffect(() => {
    // Clear fresh validation state when file selection changes
    setFreshValidation(null);
    setValidationError(null);

    if (selectedProgram && selectedProgram.name.toUpperCase().endsWith('.NC') && !selectedProgram.is_directory) {
      fetchFilePreview(selectedProgram);
      fetchFileMetadata(selectedProgram);

      // Fetch deployment detail for O-number files
      if (isONumberFile(selectedProgram.name)) {
        setSelectedDeploymentId(null);  // Reset to current deployment
        fetchDeploymentDetail(selectedProgram);
      } else {
        setDeploymentDetail(null);
        setDeploymentError(null);
        setSelectedDeploymentId(null);
      }
    } else {
      setPreviewLines([]);
      setFileMetadata(null);
      setDeploymentDetail(null);
      setDeploymentError(null);
      setSelectedDeploymentId(null);
    }
  }, [selectedProgram]);

  // Handle deployment selection change from history dropdown
  useEffect(() => {
    if (selectedDeploymentId && deploymentDetail) {
      // User selected a historical deployment - fetch its details
      fetchSelectedDeploymentDetails(selectedDeploymentId);
    } else if (selectedDeploymentId === null && deploymentDetail) {
      // User selected current deployment (empty option) - fetch the current deployment
      // Find the current deployment entry in history (is_current = true)
      const currentEntry = deploymentDetail.history?.find(h => h.is_current);
      if (currentEntry) {
        fetchSelectedDeploymentDetails(currentEntry.id);
      }
    }
  }, [selectedDeploymentId, deploymentDetail?.history]);

  const selectedMachine = machines.find(m => m.id === selectedMachineId);

  const toggleToolExpanded = (toolNumber: number) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(toolNumber)) {
      newExpanded.delete(toolNumber);
    } else {
      newExpanded.add(toolNumber);
    }
    setExpandedTools(newExpanded);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 10) / 10 + ' ' + sizes[i];
  };

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const formatRuntime = (seconds: number) => {
    if (!seconds) return '─ unknown ─';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const extractONumber = (filename: string): string | null => {
    const match = filename.match(/^O(\d{4})\.nc$/i);
    return match ? match[1] : null;
  };

  const isONumberFile = (filename: string): boolean => {
    return extractONumber(filename) !== null;
  };

  // Get the currently displayed deployment (either selected from history or current)
  // @ts-ignore - reserved for future use
  const getCurrentDisplayedDeployment = () => {
    if (!deploymentDetail) return null;

    // If a specific deployment is selected from history, find and return it
    if (selectedDeploymentId && deploymentDetail.history) {
      const selected = deploymentDetail.history.find(h => h.id === selectedDeploymentId);
      if (selected) {
        // Return a combined object with the selected history entry merged with full details
        // For now, we'll reconstruct from the history entry
        return {
          deployment: selected,
          isHistorical: true
        };
      }
    }

    // Otherwise return current deployment
    return {
      deployment: deploymentDetail.deployment,
      isHistorical: false
    };
  };

  // Animated ASCII progress bar during metadata parsing
  const [progressState, setProgressState] = React.useState(0);

  React.useEffect(() => {
    if (!metadataLoading) return;

    const interval = setInterval(() => {
      setProgressState(prev => (prev + 1) % 8);
    }, 900);

    return () => clearInterval(interval);
  }, [metadataLoading]);

  const renderProgressBar = () => {
    const stages = [
      '[████░░░░░]',
      '[██████░░░]',
      '[████████░]',
      '[██████████]',
      '[██████████]',
      '[████████░░]',
      '[██████░░░░]',
      '[████░░░░░░]',
    ];
    return <span className="ascii-progress-container">{stages[progressState]} PARSING...</span>;
  };

  const handleItemClick = (program: Program) => {
    if (program.is_directory) {
      // Navigate into directory
      if (program.name === '..') {
        // Go up one level
        const parentPath = (currentPath || '/').split('/').slice(0, -1).join('/') || '/';
        setCurrentPath(parentPath);
      } else {
        // Navigate into subdirectory
        const basePath = currentPath || '/';
        const newPath = basePath === '/' ? `/${program.name}` : `${basePath}/${program.name}`;
        setCurrentPath(newPath);
      }
    } else {
      // Select file to show details
      setSelectedProgram(program);
    }
  };

  const handleDownload = async (program: Program) => {
    if (!selectedMachineId || !currentPath) return;

    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/download?file_path=${encodeURIComponent(filePath)}`;

      const response = await fetch(url);
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        } catch {
          throw new Error(`HTTP ${response.status}`);
        }
      }

      // Create blob and download
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = program.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('Download error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(`Download failed: ${errorMessage}`);
    }
  };

  const fetchFilePreview = async (program: Program) => {
    if (!selectedMachineId || !currentPath) return;

    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/view?file_path=${encodeURIComponent(filePath)}`;

      const response = await fetch(url);
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        } catch {
          throw new Error(`HTTP ${response.status}`);
        }
      }

      const data: ViewData = await response.json();
      const lines = data.content.split('\n');
      setPreviewLines(lines.slice(0, 50));
    } catch (err) {
      console.error('Preview error:', err);
      setPreviewLines(['Error loading preview']);
    }
  };

  const fetchFileMetadata = async (program: Program) => {
    if (!selectedMachineId || !currentPath) return;

    setMetadataLoading(true);
    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/metadata?file_path=${encodeURIComponent(filePath)}`;

      const response = await fetch(url);
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        } catch {
          throw new Error(`HTTP ${response.status}`);
        }
      }

      const data: FileMetadata = await response.json();
      setFileMetadata(data);
    } catch (err) {
      console.error('Metadata error:', err);
      setFileMetadata(null);
    } finally {
      setMetadataLoading(false);
    }
  };

  const fetchDeploymentDetail = async (program: Program) => {
    if (!selectedMachineId) return;

    const onumber = extractONumber(program.name);
    if (!onumber) {
      setDeploymentDetail(null);
      return;
    }

    setDeploymentLoading(true);
    setDeploymentError(null);

    try {
      const url = `${API_BASE_URL}/api/programs/machines/${selectedMachineId}/deployments/by-onumber/${onumber}?include_history=true`;
      const response = await fetch(url);

      if (!response.ok) {
        if (response.status === 404) {
          setDeploymentDetail(null);
          setDeploymentError('No deployment record found');
          return;
        }
        throw new Error(`HTTP ${response.status}`);
      }

      const data: DeploymentDetail = await response.json();
      setDeploymentDetail(data);
    } catch (err) {
      console.error('Deployment detail error:', err);
      setDeploymentError(err instanceof Error ? err.message : 'Failed to load');
      setDeploymentDetail(null);
    } finally {
      setDeploymentLoading(false);
    }
  };

  // Fetch full deployment details by ID from history
  const fetchSelectedDeploymentDetails = async (deploymentId: number) => {
    if (!deploymentDetail || !deploymentDetail.history) return;

    // Find the deployment in history
    const historyEntry = deploymentDetail.history.find(h => h.id === deploymentId);
    if (!historyEntry) return;

    setDeploymentLoading(true);
    setDeploymentError(null);

    try {
      // Query to get full deployment details by ID
      const response = await fetch(`${API_BASE_URL}/api/programs/deployments/${deploymentId}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const deploymentData = await response.json();

      // Update deploymentDetail with selected deployment while keeping history
      setDeploymentDetail({
        ...deploymentDetail,
        deployment: deploymentData.deployment || deploymentData
      });
    } catch (err) {
      console.error('Error fetching selected deployment:', err);
      setDeploymentError('Failed to load selected deployment');
    } finally {
      setDeploymentLoading(false);
    }
  };

  const handleViewCode = async (program: Program) => {
    if (!selectedMachineId || !currentPath) return;

    setViewModalLoading(true);
    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/view?file_path=${encodeURIComponent(filePath)}`;

      const response = await fetch(url);
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        } catch {
          throw new Error(`HTTP ${response.status}`);
        }
      }

      const data: ViewData = await response.json();
      setViewModalContent(data);
      setViewModalOpen(true);
    } catch (err) {
      console.error('View error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(`View failed: ${errorMessage}`);
    } finally {
      setViewModalLoading(false);
    }
  };

  const handleValidate = async (program: Program) => {
    if (!selectedMachineId || !currentPath) return;

    setValidationLoading(true);
    setValidationError(null);
    setFreshValidation(null);

    try {
      // Step 1: Validate the file
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const validateUrl = `${API_BASE_URL}/api/programs/machines/${selectedMachineId}/programs/validate-file?file_path=${encodeURIComponent(filePath)}`;

      const validateResponse = await fetch(validateUrl, { method: 'POST' });
      if (!validateResponse.ok) {
        try {
          const errorData = await validateResponse.json();
          throw new Error(errorData.detail || `HTTP ${validateResponse.status}`);
        } catch {
          throw new Error(`HTTP ${validateResponse.status}`);
        }
      }

      const validationData = await validateResponse.json();

      // Show fresh validation results temporarily
      setFreshValidation({
        validation: validationData.validation,
        gcode_content: validationData.gcode_content,
        timestamp: Date.now()
      });

      // Step 2: Automatically save validation to database
      const deployUrl = `${API_BASE_URL}/api/programs/machines/${selectedMachineId}/programs/deploy-validated`;
      const deployResponse = await fetch(deployUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deployed_filename: program.name,
          gcode_content: validationData.gcode_content,
          validation_results: validationData.validation
        })
      });

      if (!deployResponse.ok) {
        console.warn('Failed to save validation to database');
      }

      // Step 3: Refresh deployment details to show the new record
      await fetchDeploymentDetail(program);

      // Clear fresh validation state after saving
      setFreshValidation(null);

      // Step 4: Scroll to deployment section to show updated validation
      setTimeout(() => {
        deploymentSectionRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }, 100);

    } catch (err) {
      console.error('Validation error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setValidationError(`Validation failed: ${errorMessage}`);
    } finally {
      setValidationLoading(false);
    }
  };

  // @ts-ignore - reserved for future use
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedMachineId || !currentPath) return;

    const uploadPath = currentPath === '/' ? `/${file.name}` : `${currentPath}/${file.name}`;
    const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/upload?file_path=${encodeURIComponent(uploadPath)}`;

    // Show upload progress entry in the file list
    setUploadProgress({ fileName: file.name, percent: 0 });
    setError(null);

    const xhr = new XMLHttpRequest();

    // Track upload progress
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percentComplete = Math.round((e.loaded / e.total) * 100);
        setUploadProgress({ fileName: file.name, percent: percentComplete });
      }
    });

    // Handle completion
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        setUploadProgress(null);
        setError(null);
        // Highlight the uploaded file for 5 seconds
        setHighlightedFile(file.name);
        setTimeout(() => setHighlightedFile(null), 5000);
        // Refresh the file list
        const programsUrl = `${API_BASE_URL}/api/machines/${selectedMachineId}/programs?path=${encodeURIComponent(currentPath)}`;
        fetch(programsUrl)
          .then(res => res.json())
          .then(data => {
            setPrograms(data.programs || []);
          })
          .catch(err => console.error('Error refreshing programs:', err));
      } else {
        try {
          const response = JSON.parse(xhr.responseText);
          const errorMsg = response.detail || `HTTP ${xhr.status}`;
          setError(`Upload failed: ${errorMsg}`);
        } catch {
          setError(`Upload failed: HTTP ${xhr.status}`);
        }
        setUploadProgress(null);
      }
    });

    // Handle errors
    xhr.addEventListener('error', () => {
      setError('Upload failed: Network error');
      setUploadProgress(null);
    });

    xhr.addEventListener('abort', () => {
      setError('Upload cancelled');
      setUploadProgress(null);
    });

    // Send the file
    const formData = new FormData();
    formData.append('file', file);
    xhr.open('POST', url);
    xhr.send(formData);

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Sort and prepare display list
  const displayPrograms = (() => {
    // Separate directories and files
    const directories = programs.filter(p => p.is_directory).sort((a, b) => a.name.localeCompare(b.name));
    const files = programs.filter(p => !p.is_directory).sort((a, b) => a.name.localeCompare(b.name));

    // Combine: directories first, then files
    const sorted = [...directories, ...files];

    // Add parent directory entry at the top if not at root
    return currentPath !== '/'
      ? [{ name: '..', size: 0, modified: '', is_directory: true, path: '..' }, ...sorted]
      : sorted;
  })();

  return (
    <div className="file-browser">
      {/* Header */}
      <div className="file-browser-header">
        <div className="header-title">
          <span className="text-glow-strong">FILE MANAGER</span>
        </div>
        <div className="header-actions"></div>
      </div>

      <div className="file-browser-divider">
        ╠{'═'.repeat(100)}╣
      </div>

      {/* Machine Selector */}
      <div className="machine-selector-bar">
        <label className="selector-label">MACHINE:</label>
        <select
          className="terminal-select"
          value={selectedMachineId || ''}
          onChange={(e) => setSelectedMachineId(Number(e.target.value))}
        >
          {machines.map(machine => (
            <option key={machine.id} value={machine.id}>
              {machine.name} ({machine.ip_address})
            </option>
          ))}
        </select>
        {selectedMachine && (
          <span className="machine-status">
            <StatusIndicator status="online" label="" />
          </span>
        )}
      </div>

      <div className="file-browser-content">
        {/* Programs List */}
        <div className="programs-panel">
          <div className="panel-header">
            ┌─ NC PROGRAMS (/CNC_MEM/) {'─'.repeat(50)}┐
          </div>

          {loading && !pendingFileSelection && (
            <div className="panel-loading">
              <span className="pulse">LOADING PROGRAMS...</span>
            </div>
          )}

          {loading && pendingFileSelection && (
            <div className="panel-loading">
              <span className="pulse">LOADING {pendingFileSelection}...</span>
            </div>
          )}

          {error && (
            <div className="panel-error text-error">
              ERROR: {error}
            </div>
          )}

          {!loading && !error && programs.length === 0 && (
            <div className="panel-empty text-muted">
              NO PROGRAMS FOUND
            </div>
          )}

          {!loading && !error && programs.length > 0 && (
            <div className="programs-table">
              <div className="table-header">
                <div className="col-name">NAME</div>
                <div className="col-size">SIZE</div>
                <div className="col-modified">MODIFIED</div>
                <div className="col-actions">ACTIONS</div>
              </div>
              <div className="table-divider">
                ├{'─'.repeat(80)}┤
              </div>
              <div className="table-body">
                {displayPrograms.map((program, idx) => (
                  <div
                    key={idx}
                    ref={selectedProgram?.name === program.name ? selectedProgramRef : null}
                    className={`table-row ${selectedProgram?.name === program.name ? 'selected' : ''}`}
                    onClick={() => handleItemClick(program)}
                  >
                    <div className="col-name">
                      {program.is_directory ? '/ ' : (selectedProgram?.name === program.name ? '► ' : '  ')}
                      {program.name}
                    </div>
                    <div className="col-size">{program.is_directory ? '<DIR>' : formatBytes(program.size)}</div>
                    <div className="col-modified">{formatDate(program.modified)}</div>
                    <div className="col-actions">
                      {!program.is_directory && (
                        <button
                          className="terminal-button-sm"
                          onClick={() => handleDownload(program)}
                        >
                          DL
                        </button>
                      )}
                      {program.is_directory && (
                        <span className="col-action-spacer"></span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div className="table-footer">
                └{'─'.repeat(80)}┘
              </div>
              <div className="table-summary">
                {programs.length} PROGRAMS │ TOTAL: {formatBytes(programs.reduce((sum, p) => sum + p.size, 0))}
              </div>
            </div>
          )}
        </div>

        {/* Program Details Panel */}
        {selectedProgram && (
          <div className="details-panel">
            <div className="panel-header">
              ┌─ SELECTED: {selectedProgram.name} {'─'.repeat(30)}┐
            </div>
            <div className="details-content" style={{ overflow: 'auto' }}>
              {/* FILE INFO SECTION */}
              <div className="detail-section">
                <div className="section-title">FILE INFO</div>
                <div className="detail-row">
                  <span className="label">SIZE:</span>
                  <span className="value">{formatBytes(selectedProgram.size)}</span>
                </div>
                <div className="detail-row">
                  <span className="label">MODIFIED:</span>
                  <span className="value">{formatDate(selectedProgram.modified)}</span>
                </div>
              </div>

              {/* DEPLOYMENT INFO SECTION (O-number files only) */}
              {isONumberFile(selectedProgram.name) && (
                <div className="detail-section" ref={deploymentSectionRef}>
                  <div className="deployment-info-header">
                    <div className="section-title">
                      {freshValidation ? (
                        <span style={{ color: '#4ade80' }}>*FRESH* VALIDATION RESULTS</span>
                      ) : (
                        'DEPLOYMENT INFO'
                      )}
                    </div>
                    {freshValidation && (
                      <span className="validation-timestamp text-muted">
                        Validated: {new Date(freshValidation.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                    {!freshValidation && deploymentDetail?.history && deploymentDetail.history.length > 1 && (
                      <select
                        className="deployment-selector"
                        value={selectedDeploymentId || ''}
                        onChange={(e) => setSelectedDeploymentId(e.target.value ? parseInt(e.target.value) : null)}
                      >
                        <option value="">
                          {deploymentDetail.program?.original_filename} ({formatDate(deploymentDetail.deployment.deployed_at)}) - CURRENT
                        </option>
                        {deploymentDetail.history.slice(1).map((entry) => (
                          <option key={entry.id} value={entry.id}>
                            {entry.original_filename} ({formatDate(entry.deployed_at)})
                          </option>
                        ))}
                      </select>
                    )}
                  </div>

                  {validationError && (
                    <div className="validation-error">
                      <div className="detail-row">
                        <span className="value text-error">X {validationError}</span>
                      </div>
                      <div className="error-actions">
                        <button
                          className="terminal-button-sm"
                          onClick={() => handleValidate(selectedProgram)}
                        >
                          [ RETRY ]
                        </button>
                        <button
                          className="terminal-button-sm"
                          onClick={() => setValidationError(null)}
                        >
                          [ DISMISS ]
                        </button>
                      </div>
                    </div>
                  )}

                  {freshValidation ? (
                    <>
                      <div className="detail-row">
                        <span className="label">STATUS:</span>
                        <span className={`value ${freshValidation.validation.valid ? 'text-success' : 'text-error'}`}>
                          {freshValidation.validation.valid ? '✓ PASSED' : '✕ FAILED'}
                        </span>
                      </div>

                      {(() => {
                        const age = Date.now() - freshValidation.timestamp;
                        const STALE_MS = 5 * 60 * 1000;
                        return age > STALE_MS && (
                          <div className="detail-row">
                            <span className="value text-warning">
                              ! Validation is {Math.floor(age / 60000)} minutes old. Machine state may have changed.
                            </span>
                          </div>
                        );
                      })()}

                      {freshValidation.validation.errors && freshValidation.validation.errors.length > 0 && (
                        <div className="detail-row">
                          <span className="label">ERRORS:</span>
                          <div className="value text-error">
                            {freshValidation.validation.errors.map((err, i) => (
                              <div key={i}>- {err}</div>
                            ))}
                          </div>
                        </div>
                      )}

                      {freshValidation.validation.warnings && freshValidation.validation.warnings.length > 0 && (
                        <div className="detail-row">
                          <span className="label">WARNINGS:</span>
                          <div className="value text-warning">
                            {freshValidation.validation.warnings.map((warn, i) => (
                              <div key={i}>- {warn}</div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      {deploymentLoading && (
                        <div className="detail-row">
                          <span className="value">{renderProgressBar()}</span>
                        </div>
                      )}
                      {deploymentError && (
                        <div className="detail-row">
                          <span className="value text-error">{deploymentError}</span>
                        </div>
                      )}
                      {deploymentDetail && (
                        <>
                          <div className="detail-row">
                            <span className="label">DEPLOYED:</span>
                            <span className="value">
                              {formatDate(deploymentDetail.deployment.deployed_at)}
                            </span>
                          </div>
                          <div className="detail-row">
                            <span className="label">POSTED DATE:</span>
                            <span className="value">
                              {deploymentDetail.program?.posted_date ? formatDate(deploymentDetail.program.posted_date) : 'N/A'}
                            </span>
                          </div>
                          <div className="detail-row">
                            <span className="label">RUNTIME:</span>
                            <span className="value">
                              {formatRuntime(deploymentDetail.program?.estimated_runtime_seconds || 0)}
                            </span>
                          </div>
                          <div className="detail-row">
                            <span className="label">VALIDATION:</span>
                            <span className={`value ${
                              deploymentDetail.deployment.validation_passed === null ? 'text-muted' :
                              deploymentDetail.deployment.validation_passed ? 'text-success' : 'text-error'
                            }`}>
                              {deploymentDetail.deployment.validation_passed === null ? '─ not validated ─' :
                               deploymentDetail.deployment.validation_passed ? '✓ PASSED' : '✕ FAILED'}
                            </span>
                          </div>
                        </>
                      )}
                    </>
                  )}
                </div>
              )}


              {/* TOOL DETAILS TABLE (O-number files with deployment) */}
              {((deploymentDetail?.deployment?.validation_results?.tools && !freshValidation) ||
                (freshValidation?.validation?.tools)) && (
                <div className="detail-section">
                  <div className="section-title">TOOLS</div>
                  <div className="tools-table">
                    <table className="detail-table">
                      <thead>
                        <tr>
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
                        {Object.entries((freshValidation?.validation?.tools || deploymentDetail?.deployment?.validation_results?.tools || {})).map(([toolKey, validation]: [string, any]) => {
                          const toolNumber = parseInt(toolKey) || toolKey;
                          const isExpanded = expandedTools.has(toolNumber);

                          // Check if tool is not referenced in NC (required values are 0)
                          const notInNC = validation.required_diameter === 0 && validation.required_length === 0;

                          if (notInNC) {
                            // Tool is available on machine but not referenced in NC program
                            return (
                              <tr key={toolNumber} className="tool-summary-row">
                                <td className="text-muted">─</td>
                                <td>T{String(toolNumber).padStart(2, '0')}</td>
                                <td>
                                  Ø{(validation.machine_tool_data?.diameter || 0).toFixed(3)}" L{(validation.machine_tool_data?.length || 0).toFixed(2)}"
                                  {validation.machine_tool_data?.tool_name && (
                                    <span className="text-muted"> ({validation.machine_tool_data.tool_name})</span>
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
                          const toolPassed = validation.available && validation.diameter_match && validation.length_sufficient;
                          const hasError = !validation.available || !validation.length_sufficient;
                          const hasWarning = validation.available && !validation.diameter_match;
                          const statusClass = hasError ? 'text-error' : hasWarning ? 'text-warning' : 'text-success';
                          const statusIcon = hasError ? '✕' : hasWarning ? '⚠' : '✓';
                          const expandIcon = isExpanded ? '▼' : '▶';

                          // Calculate values
                          const actualLength = validation.machine_tool_data?.length || 0;
                          const requiredLength = validation.required_length || 0;
                          const lengthDiff = actualLength - requiredLength;

                          const actualDiameter = validation.machine_tool_data?.diameter || 0;
                          const requiredDiameter = validation.required_diameter || 0;
                          const diameterDiff = actualDiameter - requiredDiameter;

                          return (
                            <React.Fragment key={toolNumber}>
                              {/* Summary Row */}
                              <tr
                                className="tool-summary-row clickable"
                                onClick={() => validation.available && toggleToolExpanded(toolNumber)}
                                style={{ cursor: validation.available ? 'pointer' : 'default' }}
                              >
                                <td className={statusClass}>{statusIcon}</td>
                                <td>
                                  {validation.available && <span className="expand-icon">{expandIcon}</span>}
                                  T{String(toolNumber).padStart(2, '0')}
                                </td>
                                <td colSpan={4}>
                                  {!validation.available ? (
                                    <span className="text-error">NOT AVAILABLE</span>
                                  ) : (
                                    <>
                                      {validation.machine_tool_data?.tool_name && (
                                        <span className="text-muted">{validation.machine_tool_data.tool_name}</span>
                                      )}
                                    </>
                                  )}
                                </td>
                                <td className={statusClass}>
                                  {toolPassed ? 'PASS' : 'FAIL'}
                                </td>
                              </tr>

                              {/* Detail Rows - Length */}
                              {isExpanded && validation.available && (
                                <tr className="tool-detail-row">
                                  <td></td>
                                  <td className="detail-label">Length</td>
                                  <td>{actualLength.toFixed(2)}"</td>
                                  <td>{requiredLength.toFixed(2)}"</td>
                                  <td className={validation.length_sufficient ? 'text-success' : 'text-error'}>
                                    {lengthDiff.toFixed(2)}"
                                  </td>
                                  <td>-</td>
                                  <td className={validation.length_sufficient ? 'text-success' : 'text-error'}>
                                    {validation.length_sufficient ? '✓' : '✕'}
                                  </td>
                                </tr>
                              )}

                              {/* Detail Rows - Diameter */}
                              {isExpanded && validation.available && (
                                <tr className="tool-detail-row">
                                  <td></td>
                                  <td className="detail-label">Diameter</td>
                                  <td>{actualDiameter.toFixed(3)}"</td>
                                  <td>{requiredDiameter.toFixed(3)}"</td>
                                  <td className={validation.diameter_match ? 'text-success' : 'text-error'}>
                                    {diameterDiff.toFixed(3)}"
                                  </td>
                                  <td>-</td>
                                  <td className={validation.diameter_match ? 'text-success' : 'text-error'}>
                                    {validation.diameter_match ? '✓' : '✕'}
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* WCS VALIDATION TABLE */}
              {((deploymentDetail?.deployment?.validation_results?.wcs_offset && !freshValidation) ||
                (freshValidation?.validation?.wcs_offset)) && (() => {
                const wcs = freshValidation?.validation?.wcs_offset || deploymentDetail?.deployment?.validation_results?.wcs_offset;
                if (!wcs) return null;

                // Check if WCS was not specified in NC (expected values are all 0)
                const notInNC = wcs.expected.x === 0 && 
                                wcs.expected.y === 0 && 
                                wcs.expected.z === 0 &&
                                wcs.warnings?.some((w: string) => w.includes("not specified in NC"));

                if (notInNC) {
                  // WCS not specified in NC - show collapsed summary with machine data
                  const expandIcon = expandedWCS ? '▼' : '▶';
                  
                  return (
                    <div className="detail-section">
                      <div className="section-title">WCS OFFSET</div>
                      <div className="wcs-validation">
                        <table className="detail-table">
                          <thead>
                            <tr>
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
                              className="wcs-summary-row clickable"
                              onClick={() => setExpandedWCS(!expandedWCS)}
                              style={{ cursor: 'pointer' }}
                            >
                              <td className="text-warning">⚠</td>
                              <td>
                                <span className="expand-icon">{expandIcon}</span>
                                G{wcs.work_offset}
                              </td>
                              <td colSpan={4} className="text-muted">
                                XYZ NOT PARSED
                              </td>
                              <td className="text-warning">WARN</td>
                            </tr>

                            {expandedWCS && ['x', 'y', 'z'].map((axis) => {
                              const actual = (wcs.actual as any)[axis];
                              return (
                                <tr key={axis} className="wcs-detail-row">
                                  <td></td>
                                  <td className="detail-label">{axis.toUpperCase()}</td>
                                  <td>{(actual || 0).toFixed(4)}"</td>
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
                    </div>
                  );
                }

                // WCS found in NC - show validation results
                const withinTolerance = wcs.within_tolerance;
                const statusClass = withinTolerance ? 'text-success' : 'text-error';
                const statusIcon = withinTolerance ? '✓' : '✕';
                const expandIcon = expandedWCS ? '▼' : '▶';

                return (
                  <div className="detail-section">
                    <div className="section-title">WCS OFFSET</div>
                    <div className="wcs-validation">
                      <table className="detail-table">
                        <thead>
                          <tr>
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
                            className="wcs-summary-row clickable"
                            onClick={() => setExpandedWCS(!expandedWCS)}
                            style={{ cursor: 'pointer' }}
                          >
                            <td className={statusClass}>{statusIcon}</td>
                            <td>
                              <span className="expand-icon">{expandIcon}</span>
                              G{wcs.work_offset}
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
                            const expected = (wcs.expected as any)[axis];
                            const actual = (wcs.actual as any)[axis];
                            const difference = (wcs.difference as any)[axis];
                            const diff = Math.abs(difference || 0);
                            const withinTol = diff <= (wcs.tolerance || 0.1);

                            return (
                              <tr key={axis} className="wcs-detail-row">
                                <td></td>
                                <td className="detail-label">{axis.toUpperCase()}</td>
                                <td>{(actual || 0).toFixed(4)}"</td>
                                <td>{(expected || 0).toFixed(4)}"</td>
                                <td className={withinTol ? 'text-success' : 'text-error'}>
                                  {diff.toFixed(4)}"
                                </td>
                                <td>±{(wcs.tolerance || 0.1).toFixed(4)}</td>
                                <td className={withinTol ? 'text-success' : 'text-error'}>
                                  {withinTol ? '✓' : '✕'}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })()}

              {/* ACTIONS SECTION */}
              <div className="detail-actions">
                <button
                  className="terminal-button"
                  onClick={() => handleDownload(selectedProgram)}
                >
                  [ DOWNLOAD ]
                </button>
                {selectedProgram.name.toUpperCase().endsWith('.NC') && (
                  <button
                    className="terminal-button"
                    onClick={() => handleViewCode(selectedProgram)}
                  >
                    [ VIEW CODE ]
                  </button>
                )}
                {selectedProgram.name.match(/^O\d{4}\.NC$/i) && (
                  validationLoading ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span>{renderProgressBar()}</span>
                      <span className="text-muted">Downloading and validating...</span>
                    </div>
                  ) : (
                    <button
                      className="terminal-button"
                      onClick={() => handleValidate(selectedProgram)}
                    >
                      [ VALIDATE ]
                    </button>
                  )
                )}
              </div>

              {/* CODE PREVIEW SECTION */}
              {previewLines.length > 0 && selectedProgram.name.toUpperCase().endsWith('.NC') && (
                <div className="code-preview">
                  <div className="preview-header">┌─ PREVIEW (First 50 Lines) ─────────────┐</div>
                  <div className="preview-content">
                    {previewLines.map((line, idx) => (
                      <div key={idx} className="preview-line">
                        <span className="line-number">{idx + 1}</span>
                        <span className="line-text">{line || ' '}</span>
                      </div>
                    ))}
                  </div>
                  <div className="preview-footer">└─────────────────────────────────────┘</div>
                </div>
              )}
            </div>
            <div className="panel-footer">
              └{'─'.repeat(50)}┘
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="file-browser-footer">
        <div className="file-browser-divider">
          ╠{'═'.repeat(100)}╣
        </div>
        <div className="command-line">
          <span className="prompt">&gt;</span>
          <span>
            {selectedMachine ? `VIEWING: ${selectedMachine.name}` : 'NO MACHINE SELECTED'}
          </span>
          <span className="separator">│</span>
          <span className="text-dim">PROGRAMS: {programs.length}</span>
        </div>
      </div>

      {/* View Modal */}
      {viewModalOpen && (
        <div className="modal-overlay" onClick={() => setViewModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">
                {viewModalContent?.file_path || 'FILE VIEWER'}
              </span>
              <button
                className="modal-close"
                onClick={() => setViewModalOpen(false)}
              >
                ✕
              </button>
            </div>

            {viewModalLoading && (
              <div className="modal-loading">
                <span className="pulse">LOADING...</span>
              </div>
            )}

            {!viewModalLoading && viewModalContent && (
              <div className="modal-body">
                <div className="file-stats">
                  <span>SIZE: {(viewModalContent.size / 1024).toFixed(2)} KB</span>
                  <span>│</span>
                  <span>LINES: {viewModalContent.lines}</span>
                </div>
                <div className="code-viewer">
                  {viewModalContent.content.split('\n').map((line, idx) => (
                    <div key={idx} className="code-line">
                      <span className="line-number">{idx + 1}</span>
                      <span className="line-content">{line || ' '}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="modal-footer">
              <button className="terminal-button" onClick={() => setViewModalOpen(false)}>
                [ CLOSE ]
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Hidden file input for uploads */}
      <input
        ref={fileInputRef}
        type="file"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      {/* Upload progress indicator */}
      {uploadProgress && (
        <div className="upload-progress-indicator">
          <span>{uploadProgress.fileName}: {uploadProgress.percent}%</span>
        </div>
      )}
    </div>
  );
};
