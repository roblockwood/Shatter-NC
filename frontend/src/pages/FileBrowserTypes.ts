export interface Program {
  name: string;
  size: number;
  modified: string;
  is_directory: boolean;
  path: string;
  program_note?: string | null;
}

export interface Machine {
  id: number;
  name: string;
  ip_address: string;
  path?: string;
}

export interface ViewData {
  file_path: string;
  content: string;
  size: number;
  lines: number;
}

export interface FileMetadata {
  file_path: string;
  tools: number[];
  runtime_seconds: number;
  has_errors: boolean;
  program_note?: string | null;
}

export interface ToolDetail {
  tool_number: number;
  diameter: number;
  corner_radius: number;
  description: string;
  length_total: number;
}

export interface ToolValidation {
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
  // Tolerance values from machine settings (not from NC file)
  diameter_tolerance?: number;
  length_tolerance_plus?: number;
  length_tolerance_minus?: number;
}

export interface WCSValidation {
  valid: boolean;
  work_offset: number;
  expected: { x: number; y: number; z: number };
  actual: { x: number; y: number; z: number };
  difference: { x: number; y: number; z: number };
  tolerance: number;
  within_tolerance: boolean;
  warnings: string[];
}

export interface ValidationResults {
  valid: boolean;
  tools: { [key: number]: ToolValidation };
  wcs_offset?: WCSValidation;
  warnings: string[];
  errors: string[];
}

export interface FreshValidationState {
  validation: ValidationResults;
  gcode_content: string;
  timestamp: number;
}

export interface DeploymentHistoryEntry {
  id: number;
  deployed_at: string;
  validation_passed: boolean | null;
  replaced_at: string | null;
  is_current: boolean;
  program_version: number | null;
  original_filename: string | null;
}

export interface DeploymentDetail {
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
      wcs_offset?: WCSValidation;
      stock_size?: Record<string, number>;
    };
    file_size_bytes: number;
    line_count: number;
  } | null;
  history?: DeploymentHistoryEntry[];
}
