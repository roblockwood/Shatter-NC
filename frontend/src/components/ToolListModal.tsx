import React from 'react';
import { Modal } from './ui/Modal';
import { formatDimension } from '../utils/formatDimension';
import type { UnitType } from '../utils/formatDimension';
import './ToolListModal.css';

interface Tool {
  tool_number: number;
  tool_name: string;
  diameter: number;
  length: number;
}

interface ToolListModalProps {
  isOpen: boolean;
  onClose: () => void;
  tools: Tool[];
  machineName: string;
  units?: UnitType;
}

export const ToolListModal: React.FC<ToolListModalProps> = ({
  isOpen,
  onClose,
  tools,
  machineName,
  units = 'in',
}) => {

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`${machineName} - TOOL TABLE`}>
      <div className="tool-list-wrapper">
        <div className="tool-list">
        {tools.length === 0 ? (
          <div className="no-tools">
            <p className="text-muted">NO TOOLS LOADED</p>
          </div>
        ) : (
          <table className="tool-table">
            <thead>
              <tr className="tool-table-header">
                <th>T#</th>
                <th>TOOL NAME</th>
                <th>DIAMETER</th>
                <th>LENGTH</th>
              </tr>
              <tr className="tool-table-divider">
                <td colSpan={4}>├{'─'.repeat(70)}┤</td>
              </tr>
            </thead>
            <tbody>
              {tools.map((tool, idx) => (
                <tr key={idx} className="tool-table-row">
                  <td className="tool-number">
                    T{String(tool.tool_number).padStart(2, '0')}
                  </td>
                  <td className="tool-name">{tool.tool_name}</td>
                  <td className="tool-diameter">
                    {formatDimension(tool.diameter, units)}
                  </td>
                  <td className="tool-length">
                    {formatDimension(tool.length, units)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="tool-table-divider">
                <td colSpan={4}>└{'─'.repeat(70)}┘</td>
              </tr>
              <tr className="tool-table-summary">
                <td colSpan={4}>
                  TOTAL: {tools.length} TOOL{tools.length !== 1 ? 'S' : ''} IN ATC
                </td>
              </tr>
            </tfoot>
          </table>
        )}
        </div>
      </div>
    </Modal>
  );
};
