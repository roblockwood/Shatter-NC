import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { TerminalBox } from '../ui/TerminalBox';
import { Select } from '../ui';
import { API_BASE_URL, getApiErrorMessage } from '../../config/api';
import './FileManagerPane.css';

interface Program {
  name: string;
  size: number;
  modified: string;
  is_directory: boolean;
  path: string;
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
  diameter_tolerance?: number;
  length_tolerance_plus?: number;
  length_tolerance_minus?: number;
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

interface FileManagerPaneProps {
  machineId: number;
  onExpand?: () => void;
}

export const FileManagerPane: React.FC<FileManagerPaneProps> = ({ machineId, onExpand: _onExpand }) => {
  const [searchParams] = useSearchParams();
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const deploymentSectionRef = React.useRef<HTMLDivElement>(null);
  const selectedProgramRef = React.useRef<HTMLDivElement>(null);
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
  const [_fileMetadata, setFileMetadata] = useState<FileMetadata | null>(null);
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [deploymentDetail, setDeploymentDetail] = useState<DeploymentDetail | null>(null);
  const [deploymentLoading, setDeploymentLoading] = useState(false);
  const [deploymentError, setDeploymentError] = useState<string | null>(null);
  const [selectedDeploymentId, setSelectedDeploymentId] = useState<number | null>(null);
  const [freshValidation, setFreshValidation] = useState<FreshValidationState | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<{ fileName: string; percent: number } | null>(null);
  const [_highlightedFile, setHighlightedFile] = useState<string | null>(null);
  const [pendingFileSelection, setPendingFileSelection] = useState<string | null>(null);
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());
  const [expandedWCS, setExpandedWCS] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'name' | 'size' | 'modified'>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [filesWithDeployments, setFilesWithDeployments] = useState<Set<string>>(new Set());

  // Handle URL parameters for navigation from upload success screen
  useEffect(() => {
    const fileParam = searchParams.get('file');
    if (fileParam && programs.length > 0 && !loading) {
      const targetProgram = programs.find(p => p.name.toUpperCase() === fileParam.toUpperCase());
      if (targetProgram) {
        setSelectedProgram(targetProgram);
        setPendingFileSelection(null);
        setTimeout(() => {
          selectedProgramRef.current?.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
          });
          setTimeout(() => {
            deploymentSectionRef.current?.scrollIntoView({
              behavior: 'smooth',
              block: 'start'
            });
          }, 300);
        }, 100);
      }
    }
  }, [searchParams, programs.length, loading]);

  // Set path when component mounts - fetch machine data to get default path
  useEffect(() => {
    setPathLoading(true);
    setCurrentPath(null);

    const controller = new AbortController();
    fetch(`${API_BASE_URL}/api/machines/${machineId}`, {
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
          console.error(`Error fetching machine ${machineId}:`, err);
          setCurrentPath('/');
          setPathLoading(false);
        }
      });

    return () => controller.abort();
  }, [machineId]);

  // Fetch programs when machine or path changes
  useEffect(() => {
    if (currentPath === null || pathLoading) {
      return;
    }

    const cacheKey = `programs_cache_${machineId}_${currentPath}`;
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) {
      try {
        const cacheData = JSON.parse(cached);
        const age = Date.now() - cacheData.timestamp;
        if (age < 60000 && cacheData.machineId === machineId && cacheData.path === currentPath) {
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

    const url = `${API_BASE_URL}/api/machines/${machineId}/programs?path=${encodeURIComponent(currentPath)}`;
    const controller = new AbortController();
    const fetchPath = currentPath;

    fetch(url, { signal: controller.signal })
      .then(res => {
        if (!res.ok) {
          return res.json().then(data => {
            const msg = getApiErrorMessage(data?.detail) || `HTTP ${res.status}`;
            throw new Error(msg);
          }).catch((e) => {
            if (e instanceof Error && !e.message.startsWith('HTTP ')) throw e;
            throw new Error(`HTTP ${res.status}`);
          });
        }
        return res.json();
      })
      .then(data => {
        if (fetchPath === currentPath) {
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
  }, [machineId, currentPath, pathLoading]);

  // Fetch deployments list for the machine
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/api/programs/machines/${machineId}/deployments`, {
      signal: controller.signal,
    })
      .then(res => {
        if (!res.ok) return [];
        return res.json();
      })
      .then((deployments: any[]) => {
        const deployedFilenames = new Set<string>();
        deployments.forEach((deployment: any) => {
          if (deployment.deployed_filename) {
            deployedFilenames.add(deployment.deployed_filename.toUpperCase());
          }
        });
        setFilesWithDeployments(deployedFilenames);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching deployments:', err);
          setFilesWithDeployments(new Set());
        }
      });

    return () => controller.abort();
  }, [machineId]);

  // Fetch preview and metadata when a .nc file is selected
  useEffect(() => {
    setFreshValidation(null);
    setValidationError(null);

    if (selectedProgram && selectedProgram.name.toUpperCase().endsWith('.NC') && !selectedProgram.is_directory) {
      fetchFilePreview(selectedProgram);
      fetchFileMetadata(selectedProgram);

      if (isONumberFile(selectedProgram.name)) {
        setSelectedDeploymentId(null);
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
  }, [selectedProgram, machineId, currentPath]);

  // Handle deployment selection change from history dropdown
  useEffect(() => {
    if (selectedDeploymentId && deploymentDetail) {
      fetchSelectedDeploymentDetails(selectedDeploymentId);
    } else if (selectedDeploymentId === null && deploymentDetail) {
      const currentEntry = deploymentDetail.history?.find(h => h.is_current);
      if (currentEntry) {
        fetchSelectedDeploymentDetails(currentEntry.id);
      }
    }
  }, [selectedDeploymentId, deploymentDetail?.history]);

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
      if (program.name === '..') {
        const parentPath = (currentPath || '/').split('/').slice(0, -1).join('/') || '/';
        setCurrentPath(parentPath);
      } else {
        const basePath = currentPath || '/';
        const newPath = basePath === '/' ? `/${program.name}` : `${basePath}/${program.name}`;
        setCurrentPath(newPath);
      }
    } else {
      setSelectedProgram(program);
    }
  };

  const handleDownload = async (program: Program) => {
    if (!currentPath) return;

    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${machineId}/download?file_path=${encodeURIComponent(filePath)}`;
      const response = await fetch(url);
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        } catch {
          throw new Error(`HTTP ${response.status}`);
        }
      }
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
    if (!currentPath) return;
    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${machineId}/view?file_path=${encodeURIComponent(filePath)}`;
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
    if (!currentPath) return;
    setMetadataLoading(true);
    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${machineId}/metadata?file_path=${encodeURIComponent(filePath)}`;
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
    const onumber = extractONumber(program.name);
    if (!onumber) {
      setDeploymentDetail(null);
      return;
    }

    setDeploymentLoading(true);
    setDeploymentError(null);

    try {
      const url = `${API_BASE_URL}/api/programs/machines/${machineId}/deployments/by-onumber/${onumber}?include_history=true`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data: DeploymentDetail = await response.json();
      if (!data.deployment) {
        setDeploymentDetail(null);
        setDeploymentError('No deployment record found');
        return;
      }
      setDeploymentDetail(data);
    } catch (err) {
      console.error('Deployment detail error:', err);
      setDeploymentError(err instanceof Error ? err.message : 'Failed to load');
      setDeploymentDetail(null);
    } finally {
      setDeploymentLoading(false);
    }
  };

  const fetchSelectedDeploymentDetails = async (deploymentId: number) => {
    if (!deploymentDetail || !deploymentDetail.history) return;
    const historyEntry = deploymentDetail.history.find(h => h.id === deploymentId);
    if (!historyEntry) return;

    setDeploymentLoading(true);
    setDeploymentError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/programs/deployments/${deploymentId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const deploymentData = await response.json();
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
    if (!currentPath) return;
    setViewModalLoading(true);
    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${machineId}/view?file_path=${encodeURIComponent(filePath)}`;
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
    if (!currentPath) return;
    setValidationLoading(true);
    setValidationError(null);
    setFreshValidation(null);

    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const validateUrl = `${API_BASE_URL}/api/programs/machines/${machineId}/programs/validate-file?file_path=${encodeURIComponent(filePath)}`;
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
      setFreshValidation({
        validation: validationData.validation,
        gcode_content: validationData.gcode_content,
        timestamp: Date.now()
      });

      const deployUrl = `${API_BASE_URL}/api/programs/machines/${machineId}/programs/deploy-validated`;
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

      await fetchDeploymentDetail(program);
      setFreshValidation(null);
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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !currentPath) return;

    const uploadPath = currentPath === '/' ? `/${file.name}` : `${currentPath}/${file.name}`;
    const url = `${API_BASE_URL}/api/machines/${machineId}/upload?file_path=${encodeURIComponent(uploadPath)}`;

    setUploadProgress({ fileName: file.name, percent: 0 });
    setError(null);

    const xhr = new XMLHttpRequest();
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percentComplete = Math.round((e.loaded / e.total) * 100);
        setUploadProgress({ fileName: file.name, percent: percentComplete });
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        setUploadProgress(null);
        setError(null);
        setHighlightedFile(file.name);
        setTimeout(() => setHighlightedFile(null), 5000);
        const programsUrl = `${API_BASE_URL}/api/machines/${machineId}/programs?path=${encodeURIComponent(currentPath)}`;
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

    xhr.addEventListener('error', () => {
      setError('Upload failed: Network error');
      setUploadProgress(null);
    });

    xhr.addEventListener('abort', () => {
      setError('Upload cancelled');
      setUploadProgress(null);
    });

    const formData = new FormData();
    formData.append('file', file);
    xhr.open('POST', url);
    xhr.send(formData);

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const displayPrograms = (() => {
    let filtered = programs;
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = programs.filter(p => 
        p.name.toLowerCase().includes(query) ||
        (p.is_directory && 'directory'.includes(query)) ||
        (!p.is_directory && 'file'.includes(query))
      );
    }

    const directories = filtered.filter(p => p.is_directory);
    const files = filtered.filter(p => !p.is_directory);

    const sortFn = (a: Program, b: Program) => {
      let comparison = 0;
      if (sortBy === 'name') {
        comparison = a.name.localeCompare(b.name);
      } else if (sortBy === 'size') {
        comparison = a.size - b.size;
      } else if (sortBy === 'modified') {
        const dateA = new Date(a.modified).getTime();
        const dateB = new Date(b.modified).getTime();
        comparison = dateA - dateB;
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    };

    const sortedDirectories = [...directories].sort(sortFn);
    const sortedFiles = [...files].sort(sortFn);
    const sorted = [...sortedDirectories, ...sortedFiles];

    return currentPath !== '/'
      ? [{ name: '..', size: 0, modified: '', is_directory: true, path: '..' }, ...sorted]
      : sorted;
  })();

  return (
    <div className="file-manager-pane">
      <TerminalBox title="FILE MANAGER" className="file-manager-terminal-box">
        <div className="file-manager-content">
          {/* Programs List */}
          <div className="file-manager-programs-panel">
            <div className="file-manager-panel-header">
              ┌─ NC PROGRAMS {currentPath ? `(${currentPath})` : ''} {'─'.repeat(30)}┐
            </div>

            {loading && !pendingFileSelection && (
              <div className="file-manager-loading">
                <span className="pulse">LOADING PROGRAMS...</span>
              </div>
            )}

            {error && (
              <div className="file-manager-error text-error">
                ERROR: {error}
              </div>
            )}

            {!loading && !error && programs.length === 0 && (
              <div className="file-manager-empty text-muted">
                NO PROGRAMS FOUND
              </div>
            )}

            {!loading && !error && programs.length > 0 && (
              <div className="file-manager-programs-table">
                <div className="file-manager-table-controls">
                  <div className="file-manager-search-container">
                    <input
                      type="text"
                      className="file-manager-search-input"
                      placeholder="SEARCH FILES..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                    {searchQuery && (
                      <button
                        className="file-manager-search-clear-btn"
                        onClick={() => setSearchQuery('')}
                        title="Clear search"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                  <div className="file-manager-sort-controls">
                    <label className="file-manager-sort-label">SORT:</label>
                    <select
                      className="file-manager-terminal-select-sm"
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value as 'name' | 'size' | 'modified')}
                    >
                      <option value="name">NAME</option>
                      <option value="size">SIZE</option>
                      <option value="modified">MODIFIED</option>
                    </select>
                    <button
                      className="file-manager-sort-direction-btn"
                      onClick={() => setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')}
                      title={`Sort ${sortDirection === 'asc' ? 'descending' : 'ascending'}`}
                    >
                      {sortDirection === 'asc' ? '↑' : '↓'}
                    </button>
                  </div>
                </div>
                <div className="file-manager-table-header">
                  <div className="file-manager-col-name">NAME</div>
                  <div className="file-manager-col-size">SIZE</div>
                  <div className="file-manager-col-modified">MODIFIED</div>
                  <div className="file-manager-col-actions">ACTIONS</div>
                </div>
                <div className="file-manager-table-divider">
                  ├{'─'.repeat(60)}┤
                </div>
                <div className="file-manager-table-body">
                  {displayPrograms.map((program, idx) => (
                    <div
                      key={idx}
                      ref={selectedProgram?.name === program.name ? selectedProgramRef : null}
                      className={`file-manager-table-row ${selectedProgram?.name === program.name ? 'selected' : ''} ${!program.is_directory && filesWithDeployments.has(program.name.toUpperCase()) ? 'has-deployment' : ''}`}
                      onClick={() => handleItemClick(program)}
                    >
                      <div className="file-manager-col-name">
                        {program.is_directory ? '/ ' : (selectedProgram?.name === program.name ? '► ' : '  ')}
                        {program.name}
                        {!program.is_directory && filesWithDeployments.has(program.name.toUpperCase()) && (
                          <span className="file-manager-deployment-indicator" title="Has deployment data">●</span>
                        )}
                      </div>
                      <div className="file-manager-col-size">{program.is_directory ? '<DIR>' : formatBytes(program.size)}</div>
                      <div className="file-manager-col-modified">{formatDate(program.modified)}</div>
                      <div className="file-manager-col-actions" onClick={(e) => e.stopPropagation()}>
                        {!program.is_directory && (
                          <>
                            <button
                              className="file-manager-terminal-button-sm"
                              onClick={() => handleDownload(program)}
                              title="Download"
                            >
                              DL
                            </button>
                            {program.name.toUpperCase().endsWith('.NC') && (
                              <button
                                className="file-manager-terminal-button-sm"
                                onClick={() => handleViewCode(program)}
                                title="View Code"
                              >
                                VC
                              </button>
                            )}
                            {program.name.match(/^O\d{4}\.NC$/i) && (
                              <button
                                className="file-manager-terminal-button-sm"
                                onClick={() => handleValidate(program)}
                                title="Validate"
                              >
                                VAL
                              </button>
                            )}
                          </>
                        )}
                        {program.is_directory && (
                          <span className="file-manager-col-action-spacer"></span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="file-manager-table-footer">
                  └{'─'.repeat(60)}┘
                </div>
                <div className="file-manager-table-summary">
                  {programs.length} PROGRAMS │ TOTAL: {formatBytes(programs.reduce((sum, p) => sum + p.size, 0))}
                </div>
              </div>
            )}

            {/* Upload button */}
            <div className="file-manager-upload-section">
              <input
                ref={fileInputRef}
                type="file"
                style={{ display: 'none' }}
                onChange={handleFileSelect}
              />
              <button
                className="file-manager-upload-button"
                onClick={() => fileInputRef.current?.click()}
              >
                [ UPLOAD FILE ]
              </button>
              {uploadProgress && (
                <span className="file-manager-upload-progress">
                  {uploadProgress.fileName}: {uploadProgress.percent}%
                </span>
              )}
            </div>
          </div>

          {/* Program Details Panel */}
          {selectedProgram && (
            <div className="file-manager-details-panel">
              <div className="file-manager-panel-header">
                ┌─ SELECTED: {selectedProgram.name} {'─'.repeat(20)}┐
              </div>
              <div className="file-manager-details-content">
                {/* FILE INFO SECTION */}
                <div className="file-manager-detail-section">
                  <div className="file-manager-section-title">FILE INFO</div>
                  <div className="file-manager-detail-row">
                    <span className="file-manager-label">SIZE:</span>
                    <span className="file-manager-value">{formatBytes(selectedProgram.size)}</span>
                  </div>
                  <div className="file-manager-detail-row">
                    <span className="file-manager-label">MODIFIED:</span>
                    <span className="file-manager-value">{formatDate(selectedProgram.modified)}</span>
                  </div>
                </div>

                {/* DEPLOYMENT INFO SECTION */}
                {isONumberFile(selectedProgram.name) && (
                  <div className="file-manager-detail-section" ref={deploymentSectionRef}>
                    <div className="file-manager-deployment-info-header">
                      <div className="file-manager-section-title">
                        {freshValidation ? (
                          <span style={{ color: '#4ade80' }}>*FRESH* VALIDATION RESULTS</span>
                        ) : (
                          'DEPLOYMENT INFO'
                        )}
                      </div>
                      {!freshValidation && deploymentDetail?.history && deploymentDetail.history.length > 1 && (
                        <Select
                          value={selectedDeploymentId?.toString() || ''}
                          onChange={(value) => setSelectedDeploymentId(value ? parseInt(value) : null)}
                          options={[
                            {
                              value: '',
                              label: `${deploymentDetail.program?.original_filename} (${formatDate(deploymentDetail.deployment.deployed_at)}) - CURRENT`
                            },
                            ...deploymentDetail.history.slice(1).map((entry) => ({
                              value: entry.id.toString(),
                              label: `${entry.original_filename} (${formatDate(entry.deployed_at)})`
                            }))
                          ]}
                          className="file-manager-deployment-selector"
                        />
                      )}
                    </div>

                    {validationError && (
                      <div className="file-manager-validation-error">
                        <div className="file-manager-detail-row">
                          <span className="file-manager-value text-error">X {validationError}</span>
                        </div>
                        <div className="file-manager-error-actions">
                          <button
                            className="file-manager-terminal-button-sm"
                            onClick={() => handleValidate(selectedProgram)}
                          >
                            [ RETRY ]
                          </button>
                          <button
                            className="file-manager-terminal-button-sm"
                            onClick={() => setValidationError(null)}
                          >
                            [ DISMISS ]
                          </button>
                        </div>
                      </div>
                    )}

                    {freshValidation ? (
                      <>
                        <div className="file-manager-detail-row">
                          <span className="file-manager-label">STATUS:</span>
                          <span className={`file-manager-value ${freshValidation.validation.valid ? 'text-success' : 'text-error'}`}>
                            {freshValidation.validation.valid ? '✓ PASSED' : '✕ FAILED'}
                          </span>
                        </div>
                        {freshValidation.validation.errors && freshValidation.validation.errors.length > 0 && (
                          <div className="file-manager-detail-row">
                            <span className="file-manager-label">ERRORS:</span>
                            <div className="file-manager-value text-error">
                              {freshValidation.validation.errors.map((err, i) => (
                                <div key={i}>- {err}</div>
                              ))}
                            </div>
                          </div>
                        )}
                        {freshValidation.validation.warnings && freshValidation.validation.warnings.length > 0 && (
                          <div className="file-manager-detail-row">
                            <span className="file-manager-label">WARNINGS:</span>
                            <div className="file-manager-value text-warning">
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
                          <div className="file-manager-detail-row">
                            <span className="file-manager-value">{renderProgressBar()}</span>
                          </div>
                        )}
                        {deploymentError && (
                          <div className="file-manager-detail-row">
                            <span className="file-manager-value text-error">{deploymentError}</span>
                          </div>
                        )}
                        {deploymentDetail && (
                          <>
                            <div className="file-manager-detail-row">
                              <span className="file-manager-label">DEPLOYED:</span>
                              <span className="file-manager-value">
                                {formatDate(deploymentDetail.deployment.deployed_at)}
                              </span>
                            </div>
                            <div className="file-manager-detail-row">
                              <span className="file-manager-label">POSTED DATE:</span>
                              <span className="file-manager-value">
                                {deploymentDetail.program?.posted_date ? formatDate(deploymentDetail.program.posted_date) : 'N/A'}
                              </span>
                            </div>
                            <div className="file-manager-detail-row">
                              <span className="file-manager-label">RUNTIME:</span>
                              <span className="file-manager-value">
                                {formatRuntime(deploymentDetail.program?.estimated_runtime_seconds || 0)}
                              </span>
                            </div>
                            <div className="file-manager-detail-row">
                              <span className="file-manager-label">VALIDATION:</span>
                              <span className={`file-manager-value ${
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

                {/* TOOL DETAILS TABLE */}
                {((deploymentDetail?.deployment?.validation_results?.tools && !freshValidation) ||
                  (freshValidation?.validation?.tools)) && (
                  <div className="file-manager-detail-section">
                    <div className="file-manager-section-title">TOOLS</div>
                    <div className="file-manager-tools-table">
                      <table className="file-manager-detail-table">
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
                            const toolNumber = parseInt(toolKey, 10);
                            if (isNaN(toolNumber)) return null;
                            const isExpanded = expandedTools.has(toolNumber);
                            const notInNC = validation.required_diameter === 0 && validation.required_length === 0;

                            if (notInNC) {
                              return (
                                <tr key={toolNumber} className="file-manager-tool-summary-row">
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

                            const toolPassed = validation.available && validation.diameter_match && validation.length_sufficient;
                            const hasError = !validation.available || !validation.length_sufficient;
                            const hasWarning = validation.available && !validation.diameter_match;
                            const statusClass = hasError ? 'text-error' : hasWarning ? 'text-warning' : 'text-success';
                            const statusIcon = hasError ? '✕' : hasWarning ? '⚠' : '✓';
                            const expandIcon = isExpanded ? '▼' : '▶';
                            const actualLength = validation.machine_tool_data?.length || 0;
                            const requiredLength = validation.required_length || 0;
                            const lengthDiff = actualLength - requiredLength;
                            const actualDiameter = validation.machine_tool_data?.diameter || 0;
                            const requiredDiameter = validation.required_diameter || 0;
                            const diameterDiff = actualDiameter - requiredDiameter;

                            return (
                              <React.Fragment key={toolNumber}>
                                <tr
                                  className="file-manager-tool-summary-row clickable"
                                  onClick={() => validation.available && toggleToolExpanded(toolNumber)}
                                  style={{ cursor: validation.available ? 'pointer' : 'default' }}
                                >
                                  <td className={statusClass}>{statusIcon}</td>
                                  <td>
                                    {validation.available && <span className="file-manager-expand-icon">{expandIcon}</span>}
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

                                {isExpanded && validation.available && (
                                  <>
                                    <tr className="file-manager-tool-detail-row">
                                      <td></td>
                                      <td className="file-manager-detail-label">Length</td>
                                      <td>{actualLength.toFixed(2)}"</td>
                                      <td>{requiredLength.toFixed(2)}"</td>
                                      <td className={validation.length_sufficient ? 'text-success' : 'text-error'}>
                                        {lengthDiff.toFixed(2)}"
                                      </td>
                                      <td>
                                        {validation.length_tolerance_plus !== undefined && validation.length_tolerance_minus !== undefined
                                          ? `+${validation.length_tolerance_plus.toFixed(4)}"/-${validation.length_tolerance_minus.toFixed(4)}"`
                                          : '-'}
                                      </td>
                                      <td className={validation.length_sufficient ? 'text-success' : 'text-error'}>
                                        {validation.length_sufficient ? '✓' : '✕'}
                                      </td>
                                    </tr>
                                    <tr className="file-manager-tool-detail-row">
                                      <td></td>
                                      <td className="file-manager-detail-label">Diameter</td>
                                      <td>{actualDiameter.toFixed(3)}"</td>
                                      <td>{requiredDiameter.toFixed(3)}"</td>
                                      <td className={validation.diameter_match ? 'text-success' : 'text-error'}>
                                        {diameterDiff.toFixed(3)}"
                                      </td>
                                      <td>
                                        {validation.diameter_tolerance !== undefined
                                          ? `±${validation.diameter_tolerance.toFixed(4)}"`
                                          : '-'}
                                      </td>
                                      <td className={validation.diameter_match ? 'text-success' : 'text-error'}>
                                        {validation.diameter_match ? '✓' : '✕'}
                                      </td>
                                    </tr>
                                  </>
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

                  const notInNC = wcs.expected.x === 0 && 
                                  wcs.expected.y === 0 && 
                                  wcs.expected.z === 0 &&
                                  wcs.warnings?.some((w: string) => w.includes("not specified in NC"));

                  if (notInNC) {
                    const expandIcon = expandedWCS ? '▼' : '▶';
                    return (
                      <div className="file-manager-detail-section">
                        <div className="file-manager-section-title">WCS OFFSET</div>
                        <div className="file-manager-wcs-validation">
                          <table className="file-manager-detail-table">
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
                                className="file-manager-wcs-summary-row clickable"
                                onClick={() => setExpandedWCS(!expandedWCS)}
                                style={{ cursor: 'pointer' }}
                              >
                                <td className="text-warning">⚠</td>
                                <td>
                                  <span className="file-manager-expand-icon">{expandIcon}</span>
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
                                  <tr key={axis} className="file-manager-wcs-detail-row">
                                    <td></td>
                                    <td className="file-manager-detail-label">{axis.toUpperCase()}</td>
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

                  const withinTolerance = wcs.within_tolerance;
                  const statusClass = withinTolerance ? 'text-success' : 'text-error';
                  const statusIcon = withinTolerance ? '✓' : '✕';
                  const expandIcon = expandedWCS ? '▼' : '▶';

                  return (
                    <div className="file-manager-detail-section">
                      <div className="file-manager-section-title">WCS OFFSET</div>
                      <div className="file-manager-wcs-validation">
                        <table className="file-manager-detail-table">
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
                              className="file-manager-wcs-summary-row clickable"
                              onClick={() => setExpandedWCS(!expandedWCS)}
                              style={{ cursor: 'pointer' }}
                            >
                              <td className={statusClass}>{statusIcon}</td>
                              <td>
                                <span className="file-manager-expand-icon">{expandIcon}</span>
                                G{wcs.work_offset}
                              </td>
                              <td colSpan={4}>
                                <span className="text-muted">X/Y/Z Coordinates</span>
                              </td>
                              <td className={statusClass}>
                                {withinTolerance ? 'PASS' : 'FAIL'}
                              </td>
                            </tr>
                            {expandedWCS && ['x', 'y', 'z'].map((axis) => {
                              const expected = (wcs.expected as any)[axis];
                              const actual = (wcs.actual as any)[axis];
                              const difference = (wcs.difference as any)[axis];
                              const diff = Math.abs(difference || 0);
                              const withinTol = diff <= (wcs.tolerance || 0.1);

                              return (
                                <tr key={axis} className="file-manager-wcs-detail-row">
                                  <td></td>
                                  <td className="file-manager-detail-label">{axis.toUpperCase()}</td>
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
                <div className="file-manager-detail-actions">
                  <button
                    className="file-manager-terminal-button"
                    onClick={() => handleDownload(selectedProgram)}
                  >
                    [ DOWNLOAD ]
                  </button>
                  {selectedProgram.name.toUpperCase().endsWith('.NC') && (
                    <button
                      className="file-manager-terminal-button"
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
                        className="file-manager-terminal-button"
                        onClick={() => handleValidate(selectedProgram)}
                      >
                        [ VALIDATE ]
                      </button>
                    )
                  )}
                </div>

                {/* CODE PREVIEW SECTION */}
                {previewLines.length > 0 && selectedProgram.name.toUpperCase().endsWith('.NC') && (
                  <div className="file-manager-code-preview">
                    <div className="file-manager-preview-header">┌─ PREVIEW (First 50 Lines) ─────────────┐</div>
                    <div className="file-manager-preview-content">
                      {previewLines.map((line, idx) => (
                        <div key={idx} className="file-manager-preview-line">
                          <span className="file-manager-line-number">{idx + 1}</span>
                          <span className="file-manager-line-text">{line || ' '}</span>
                        </div>
                      ))}
                    </div>
                    <div className="file-manager-preview-footer">└─────────────────────────────────────┘</div>
                  </div>
                )}
              </div>
              <div className="file-manager-panel-footer">
                └{'─'.repeat(50)}┘
              </div>
            </div>
          )}
        </div>
      </TerminalBox>

      {/* View Modal */}
      {viewModalOpen && (
        <div className="file-manager-modal-overlay" onClick={() => setViewModalOpen(false)}>
          <div className="file-manager-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="file-manager-modal-header">
              <span className="file-manager-modal-title">
                {viewModalContent?.file_path || 'FILE VIEWER'}
              </span>
              <button
                className="file-manager-modal-close"
                onClick={() => setViewModalOpen(false)}
              >
                ✕
              </button>
            </div>

            {viewModalLoading && (
              <div className="file-manager-modal-loading">
                <span className="pulse">LOADING...</span>
              </div>
            )}

            {!viewModalLoading && viewModalContent && (
              <div className="file-manager-modal-body">
                <div className="file-manager-file-stats">
                  <span>SIZE: {(viewModalContent.size / 1024).toFixed(2)} KB</span>
                  <span>│</span>
                  <span>LINES: {viewModalContent.lines}</span>
                </div>
                <div className="file-manager-code-viewer">
                  {viewModalContent.content.split('\n').map((line, idx) => (
                    <div key={idx} className="file-manager-code-line">
                      <span className="file-manager-line-number">{idx + 1}</span>
                      <span className="file-manager-line-content">{line || ' '}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="file-manager-modal-footer">
              <button className="file-manager-terminal-button" onClick={() => setViewModalOpen(false)}>
                [ CLOSE ]
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
