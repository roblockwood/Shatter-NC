import { describe, it } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import { FileManagerPaneDetailPanel } from '../components/machine-detail/FileManagerPaneDetailPanel';
import { Program } from '../components/machine-detail/FileManagerPaneTypes';

const mockProgram: Program = {
  name: 'O1234.NC',
  size: 2048,
  modified: '2026-04-25T10:00:00Z',
  is_directory: false,
  path: '/O1234.NC',
};

const baseProps = {
  selectedProgram: mockProgram,
  deploymentDetail: null,
  deploymentLoading: false,
  deploymentError: null,
  freshValidation: null,
  expandedTools: new Set<number>(),
  expandedWCS: false,
  selectedDeploymentId: null,
  validationError: null,
  validationLoading: false,
  previewLines: [],
  metadataLoading: false,
  deploymentSectionRef: React.createRef<HTMLDivElement>(),
  setExpandedWCS: () => {},
  setSelectedDeploymentId: () => {},
  setValidationError: () => {},
  toggleToolExpanded: () => {},
  onDownload: () => {},
  onValidate: () => {},
  onViewCode: () => {},
};

describe('FileManagerPaneDetailPanel', () => {
  it('renders without crashing', () => {
    render(<FileManagerPaneDetailPanel {...baseProps} />);
  });

  it('renders without crashing when metadataLoading is true', () => {
    render(<FileManagerPaneDetailPanel {...baseProps} metadataLoading />);
  });

  it('renders without crashing when validationLoading is true', () => {
    render(<FileManagerPaneDetailPanel {...baseProps} validationLoading />);
  });

  it('renders without crashing for a non-O-number file', () => {
    const nonOFile: Program = { ...mockProgram, name: 'FIXTURE.NC' };
    render(<FileManagerPaneDetailPanel {...baseProps} selectedProgram={nonOFile} />);
  });

  it('renders without crashing with previewLines', () => {
    render(
      <FileManagerPaneDetailPanel
        {...baseProps}
        previewLines={['G0 X0 Y0', 'M30']}
      />
    );
  });
});
