import React, { useEffect } from 'react';
import './Modal.css';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, footer }) => {
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
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-border-top">
            ╔{'═'.repeat(30)}╗
          </div>
          <div className="modal-title">
            {title}
            <button className="modal-close" onClick={onClose}>
              [✕]
            </button>
          </div>
          <div className="modal-border-middle">
            ╠{'═'.repeat(30)}╣
          </div>
        </div>
        <div className="modal-body">{children}</div>
        <div className="modal-footer">
          {footer || (
            <div className="modal-border-bottom">
              ╚{'═'.repeat(30)}╝
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
