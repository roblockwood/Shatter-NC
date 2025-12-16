import React, { useEffect } from 'react';
import './SaveConfirmModal.css';

interface SaveConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  onSave: () => void;
  machineName: string;
}

const FLOPPY_DISC_ASCII = `     ┌─────────────┐
     │             │
     │   ╔═════╗   │
     │   ║     ║   │
     │   ║  ▓▓ ║   │
     │   ║  ▓▓ ║   │
     │   ║     ║   │
     │   ╚═════╝   │
     │             │
     │   ┌─────┐   │
     │   │     │   │
     └───┴─────┴───┘`;

export const SaveConfirmModal: React.FC<SaveConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  onSave,
  machineName
}) => {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="save-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">⚠ UNSAVED CHANGES ⚠</div>
        <div className="modal-divider">
          ╠{'═'.repeat(46)}╣
        </div>
        <div className="modal-ascii-art">
          <pre>{FLOPPY_DISC_ASCII}</pre>
        </div>
        <div className="modal-message">
          SAVE BEFORE EXITING?
        </div>
        <div className="modal-warning">
          <div>MACHINE: "{machineName}"</div>
          <div style={{ marginTop: '8px' }}>
            YOU HAVE UNSAVED CHANGES.
          </div>
          <div>
            EXITING WILL DISCARD ALL MODIFICATIONS.
          </div>
          <div style={{ marginTop: '8px' }}>
            SAVE CHANGES OR DISCARD?
          </div>
        </div>
        <div className="modal-actions">
          <button className="modal-btn cancel" onClick={onClose}>
            [ CANCEL ]
          </button>
          <button className="modal-btn discard" onClick={onConfirm}>
            [ DISCARD ]
          </button>
          <button className="modal-btn save" onClick={() => {
            onClose();
            onSave();
          }}>
            [ SAVE ]
          </button>
        </div>
      </div>
    </div>
  );
};

