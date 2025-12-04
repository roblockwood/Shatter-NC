import React, { useEffect, useState } from 'react';
import './DeleteConfirmModal.css';

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  machineName: string;
}

const ASCII_ART_OPTIONS = [
  // Mushroom cloud nuke (original)
  `            _.-^^---....,,--
        _--                  --_
       <                        >)
       |                         |
        \._                   _./
           \`\`\`--. . , ; .--'''
                 | |   |
              .-=||  | |=-.
              \`-=#$%&%$#=-'
                 | ;  :|
        _____.,-#%&$@%#&#~,._____`,

  // Dr. Strangelove riding the bomb
  `          //|\\\\
         // | \\\\
        //  |  \\\\
       //   |   \\\\
      //    |    \\\\
     //     |     \\\\
    //      |      \\\\
   //       |       \\\\
  //________|________\\\\
  |    BOMB INCOMING  |
  |_____________________|
        |||  |||
       _|||__|||_
      [___    ___]
          |  |
         /|  |\\
        / |  | \\`,

  // Explosion impact
  `            *
           /|\\
          / | \\
         /  |  \\
        *   |   *
         \\  |  /
          \\ | /
           \\|/
            *
       ~~BOOM~~
         / | \\
        /  |  \\
       /   |   \\
      *    |    *
       \\   |   /
        \\  |  /
         \\ | /
          \\|/
           *`,

  // Missile launch
  `         ___
        /   \\
       | O   |
       |     |
        \\___/
          |||
          |||
          |||
      +---|||---+
      |   |||   |
      | FIRE!  |
      |   |||   |
      +---|||---+
          |||
         /||\\
        / || \\
       /  ||  \\
      /   ||   \\
     ~~~~ ~~ ~~~~`,

  // Target crosshairs with nuke
  `       + - - - - +
       |     *     |
       |    /|\\    |
       |   / | \\   |
       |  *  |  *  |
       |     |     |
     - - - -O- - - -
       |     |     |
       |  *  |  *  |
       |   \\ | /   |
       |    \\|/    |
       |     *     |
       + - - - - +`
];

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  machineName
}) => {
  const [selectedArt, setSelectedArt] = useState<string>(ASCII_ART_OPTIONS[0]);

  useEffect(() => {
    if (isOpen) {
      // Select a random ASCII art when modal opens
      const randomIndex = Math.floor(Math.random() * ASCII_ART_OPTIONS.length);
      setSelectedArt(ASCII_ART_OPTIONS[randomIndex]);
    }
  }, [isOpen]);

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
      <div className="delete-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">⚠ CONFIRM DELETION ⚠</div>
        <div className="modal-divider">
          ╠{'═'.repeat(46)}╣
        </div>
        <div className="modal-ascii-art">
          <pre>{selectedArt}</pre>
        </div>
        <div className="modal-message">
          DEFCON 1 - MACHINE TERMINATION
        </div>
        <div className="modal-warning">
          <div>TARGET: "{machineName}"</div>
          <div style={{ marginTop: '8px' }}>
            WARNING: THIS ACTION CANNOT BE UNDONE.
          </div>
          <div>
            MACHINE WILL STOP BEING MONITORED IMMEDIATELY.
          </div>
          <div style={{ marginTop: '8px' }}>
            PROCEED WITH DELETION?
          </div>
        </div>
        <div className="modal-actions">
          <button className="modal-btn cancel" onClick={onClose}>
            [ CANCEL ]
          </button>
          <button className="modal-btn delete" onClick={onConfirm}>
            [ DELETE ]
          </button>
        </div>
      </div>
    </div>
  );
};
