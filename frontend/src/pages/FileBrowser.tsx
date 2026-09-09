import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { StatusIndicator, Select } from '../components/ui';
import './FileBrowser.css';
import { API_BASE_URL, getApiErrorMessage } from '../config/api';
import type {
  Program,
  Machine,
  ViewData,
  FileMetadata,
  FreshValidationState,
  DeploymentDetail,
} from './FileBrowserTypes';
import { formatBytes, formatDate, isONumberFile, extractONumber } from './FileBrowserUtils';
import { FileBrowserDetailPanel } from './FileBrowserDetailPanel';

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
  // reserved for future use
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
  // reserved for future use
  const [_highlightedFile, setHighlightedFile] = useState<string | null>(null);
  const [pendingFileSelection, setPendingFileSelection] = useState<string | null>(null);
  // Expand/collapse state for validation tables
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());
  const [expandedWCS, setExpandedWCS] = useState(false);
  // Search and sort state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'name' | 'comment' | 'size' | 'modified'>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  // Deployment tracking - set of filenames that have deployments
  const [filesWithDeployments, setFilesWithDeployments] = useState<Set<string>>(new Set());
  const [programsRefreshKey, setProgramsRefreshKey] = useState(0);

  // Keep URL params in primitive values so effects don't depend on mutable objects.
  const deepLinkMachineParam = searchParams.get('machine');
  const deepLinkFileParam = searchParams.get('file');
  const deepLinkFilePathParam = searchParams.get('file_path');
  const deepLinkPathParam = searchParams.get('path');

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

  // Handle URL parameters for navigation from Current Program and upload flows
  useEffect(() => {
    if (deepLinkMachineParam && (deepLinkFileParam || deepLinkFilePathParam) && machines.length > 0) {
      const machineId = parseInt(deepLinkMachineParam);
      const normalizePath = (raw: string): string => {
        const normalized = `/${String(raw || '').replace(/\\/g, '/').split('/').filter(Boolean).join('/')}`;
        return normalized === '/' ? '/' : normalized;
      };

      // Set selected machine if different
      if (!isNaN(machineId) && selectedMachineId !== machineId) {
        setSelectedMachineId(machineId);
      }

      // Prefer full file path links so we navigate to the containing directory.
      if (deepLinkFilePathParam) {
        const normalizedFilePath = normalizePath(deepLinkFilePathParam);
        const parts = normalizedFilePath.split('/').filter(Boolean);
        const fileNameFromPath = parts.length > 0 ? parts[parts.length - 1] : null;

        if (fileNameFromPath) {
          setPendingFileSelection(fileNameFromPath);
        }
        return;
      }

      // Fallback for filename-only links
      if (deepLinkFileParam) {
        setPendingFileSelection(deepLinkFileParam);
      }
    }
  }, [deepLinkMachineParam, deepLinkFileParam, deepLinkFilePathParam, machines.length, selectedMachineId]);

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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingFileSelection, programs.length, loading]);

  // Set path when machine changes - fetch fresh machine data to ensure we have latest config
  useEffect(() => {
    if (selectedMachineId === null) return;

    const parsedLinkedMachine = deepLinkMachineParam ? parseInt(deepLinkMachineParam) : NaN;
    const isLinkedMachine = !isNaN(parsedLinkedMachine) && parsedLinkedMachine === selectedMachineId;
    const normalizePath = (raw: string): string => {
      const normalized = `/${String(raw || '').replace(/\\/g, '/').split('/').filter(Boolean).join('/')}`;
      return normalized === '/' ? '/' : normalized;
    };
    const linkedPath = deepLinkPathParam ? normalizePath(deepLinkPathParam) : null;

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
        const machineDefaultPath = machineData.path || '/';
        const newPath = (isLinkedMachine && linkedPath) ? linkedPath : machineDefaultPath;
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
  }, [selectedMachineId, deepLinkMachineParam, deepLinkPathParam]);

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
      } catch (_e) {
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
  }, [selectedMachineId, currentPath, pathLoading, programsRefreshKey]);

  // Fetch deployments list for the machine to mark files with deployment data
  useEffect(() => {
    if (!selectedMachineId) {
      setFilesWithDeployments(new Set());
      return;
    }

    const controller = new AbortController();
    fetch(`${API_BASE_URL}/api/programs/machines/${selectedMachineId}/deployments`, {
      signal: controller.signal,
    })
      .then(res => {
        if (!res.ok) return [];
        return res.json();
      })
      .then((deployments: { deployed_filename?: string; deployed_path?: string }[]) => {
        // Build two lookup sets for path-aware badge matching.
        // deployed_path values are stored as full remote paths (e.g. "/FOLDER_A/O0003.nc")
        // and let us correctly distinguish same-named files in different directories.
        // deployed_filename values (basename only) serve as a fallback for older records
        // that were registered before path-aware tracking was introduced.
        const deployedFilenames = new Set<string>();
        deployments.forEach((deployment) => {
          if (deployment.deployed_path) {
            deployedFilenames.add(deployment.deployed_path.toUpperCase());
          }
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
  }, [selectedMachineId]);

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
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
      if (data.program_note && selectedMachineId) {
        setPrograms((prev) =>
          prev.map((p) =>
            p.path === program.path && p.name === program.name
              ? { ...p, program_note: data.program_note }
              : p
          )
        );
        const cacheKey = `programs_cache_${selectedMachineId}_${currentPath}`;
        const cached = sessionStorage.getItem(cacheKey);
        if (cached) {
          try {
            const cacheData = JSON.parse(cached);
            cacheData.programs = (cacheData.programs || []).map((p: Program) =>
              p.path === program.path && p.name === program.name
                ? { ...p, program_note: data.program_note }
                : p
            );
            sessionStorage.setItem(cacheKey, JSON.stringify(cacheData));
          } catch {
            /* ignore stale cache */
          }
        }
      }
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
        throw new Error(`HTTP ${response.status}`);
      }

      const data: DeploymentDetail = await response.json();
      
      // Handle case where deployment is null (program running but not deployed through system)
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
          deployed_path: filePath,
          gcode_content: validationData.gcode_content,
          validation_results: validationData.validation
        })
      });

      if (!deployResponse.ok) {
        console.warn('Failed to save validation to database');
      }

      sessionStorage.removeItem(`programs_cache_${selectedMachineId}_${currentPath}`);
      setProgramsRefreshKey((key) => key + 1);

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

  // Sort and prepare display list with search and sort functionality
  const displayPrograms = (() => {
    // Filter by search query
    let filtered = programs;
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = programs.filter(p => 
        p.name.toLowerCase().includes(query) ||
        (p.program_note && p.program_note.toLowerCase().includes(query)) ||
        (p.is_directory && 'directory'.includes(query)) ||
        (!p.is_directory && 'file'.includes(query))
      );
    }

    // Separate directories and files
    const directories = filtered.filter(p => p.is_directory);
    const files = filtered.filter(p => !p.is_directory);

    // Sort function
    const sortFn = (a: Program, b: Program) => {
      let comparison = 0;
      
      if (sortBy === 'name') {
        comparison = a.name.localeCompare(b.name);
      } else if (sortBy === 'comment') {
        comparison = (a.program_note ?? '').localeCompare(b.program_note ?? '');
      } else if (sortBy === 'size') {
        comparison = a.size - b.size;
      } else if (sortBy === 'modified') {
        const dateA = new Date(a.modified).getTime();
        const dateB = new Date(b.modified).getTime();
        comparison = dateA - dateB;
      }
      
      return sortDirection === 'asc' ? comparison : -comparison;
    };

    // Sort directories and files separately
    const sortedDirectories = [...directories].sort(sortFn);
    const sortedFiles = [...files].sort(sortFn);

    // Combine: directories first, then files
    const sorted = [...sortedDirectories, ...sortedFiles];

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
        {machines.length > 0 ? (
          <Select
            value={selectedMachineId?.toString() || ''}
            onChange={(value) => setSelectedMachineId(value ? Number(value) : null)}
            options={machines.map(machine => ({
              value: machine.id.toString(),
              label: `${machine.name} (${machine.ip_address})`
            }))}
            className="terminal-select"
          />
        ) : (
          <span className="text-muted">Loading machines...</span>
        )}
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
              {/* Search and Sort Controls */}
              <div className="table-controls">
                <div className="search-container">
                  <input
                    type="text"
                    className="file-search-input"
                    placeholder="SEARCH FILES..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button
                      className="search-clear-btn"
                      onClick={() => setSearchQuery('')}
                      title="Clear search"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <div className="sort-controls">
                  <label className="sort-label">SORT:</label>
                  <Select
                    className="terminal-select-sm"
                    value={sortBy}
                    onChange={(value) => setSortBy(value as 'name' | 'comment' | 'size' | 'modified')}
                    options={[
                      { value: 'name', label: 'NAME' },
                      { value: 'comment', label: 'COMMENT' },
                      { value: 'size', label: 'SIZE' },
                      { value: 'modified', label: 'MODIFIED' },
                    ]}
                  />
                  <button
                    className="sort-direction-btn"
                    onClick={() => setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')}
                    title={`Sort ${sortDirection === 'asc' ? 'descending' : 'ascending'}`}
                  >
                    {sortDirection === 'asc' ? '↑' : '↓'}
                  </button>
                </div>
              </div>
              <div className="table-header">
                <div className="col-name">NAME</div>
                <div className="col-comment">COMMENT</div>
                <div className="col-size">SIZE</div>
                <div className="col-modified">MODIFIED</div>
                <div className="col-actions">ACTIONS</div>
              </div>
              <div className="table-divider">
                ├{'─'.repeat(80)}┤
              </div>
              <div className="table-body">
                {displayPrograms.map((program, idx) => {
                  // Check for deployment badge: prefer path-aware match, fall back to basename.
                  const filePath = ((currentPath || '/').replace(/\/$/, '') + '/' + program.name).replace('//', '/');
                  const hasDeployment = !program.is_directory && (
                    filesWithDeployments.has(filePath.toUpperCase()) ||
                    filesWithDeployments.has(program.name.toUpperCase())
                  );
                  return (
                  <div
                    key={idx}
                    ref={selectedProgram?.name === program.name ? selectedProgramRef : null}
                    className={`table-row ${selectedProgram?.name === program.name ? 'selected' : ''} ${hasDeployment ? 'has-deployment' : ''}`}
                    onClick={() => handleItemClick(program)}
                  >
                    <div className="col-name">
                      {program.is_directory ? '/ ' : (selectedProgram?.name === program.name ? '► ' : '  ')}
                      {program.name}
                      {hasDeployment && (
                        <span className="deployment-indicator" title="Has deployment data">●</span>
                      )}
                    </div>
                    <div
                      className="col-comment text-dim"
                      title={program.program_note ?? undefined}
                    >
                      {program.program_note ?? (program.is_directory ? '' : '—')}
                    </div>
                    <div className="col-size">{program.is_directory ? '<DIR>' : formatBytes(program.size)}</div>
                    <div className="col-modified">{formatDate(program.modified)}</div>
                    <div className="col-actions" onClick={(e) => e.stopPropagation()}>
                      {!program.is_directory && (
                        <>
                          <button
                            className="terminal-button-sm"
                            onClick={() => handleDownload(program)}
                            title="Download"
                          >
                            DL
                          </button>
                          {program.name.toUpperCase().endsWith('.NC') && (
                            <button
                              className="terminal-button-sm"
                              onClick={() => handleViewCode(program)}
                              title="View Code"
                            >
                              VC
                            </button>
                          )}
                          {program.name.match(/^O\d{4}\.NC$/i) && (
                            <button
                              className="terminal-button-sm"
                              onClick={() => handleValidate(program)}
                              title="Validate"
                            >
                              VAL
                            </button>
                          )}
                        </>
                      )}
                      {program.is_directory && (
                        <span className="col-action-spacer"></span>
                      )}
                    </div>
                  </div>
                  );
                })}
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
          <FileBrowserDetailPanel
            selectedProgram={selectedProgram}
            deploymentDetail={deploymentDetail}
            deploymentLoading={deploymentLoading}
            deploymentError={deploymentError}
            freshValidation={freshValidation}
            expandedTools={expandedTools}
            expandedWCS={expandedWCS}
            selectedDeploymentId={selectedDeploymentId}
            validationError={validationError}
            validationLoading={validationLoading}
            previewLines={previewLines}
            metadataLoading={metadataLoading}
            deploymentSectionRef={deploymentSectionRef}
            setExpandedWCS={setExpandedWCS}
            setSelectedDeploymentId={setSelectedDeploymentId}
            setValidationError={setValidationError}
            toggleToolExpanded={toggleToolExpanded}
            onDownload={handleDownload}
            onValidate={handleValidate}
            onViewCode={handleViewCode}
          />
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
