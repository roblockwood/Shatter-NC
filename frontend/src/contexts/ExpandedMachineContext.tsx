import React, { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

interface ExpandedMachineContextType {
  expandedMachine: {
    id: number;
    name: string;
  } | null;
  layoutEditMode: boolean;
  setExpandedMachine: (machine: { id: number; name: string } | null) => void;
  setLayoutEditMode: (mode: boolean | ((prev: boolean) => boolean)) => void;
  onCollapse: (() => void) | null;
  setOnCollapse: (handler: (() => void) | null) => void;
  onToggleLayoutEdit: (() => void) | null;
  setOnToggleLayoutEdit: (handler: (() => void) | null) => void;
  // Layout edit controls
  showPaneList: boolean;
  setShowPaneList: (show: boolean) => void;
  onResetToDefault: (() => void) | null;
  setOnResetToDefault: (handler: (() => void) | null) => void;
}

const ExpandedMachineContext = createContext<ExpandedMachineContextType | undefined>(undefined);

export const ExpandedMachineProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [expandedMachine, setExpandedMachine] = useState<{ id: number; name: string } | null>(null);
  const [layoutEditMode, setLayoutEditMode] = useState(false);
  const [onCollapse, setOnCollapse] = useState<(() => void) | null>(null);
  const [onToggleLayoutEdit, setOnToggleLayoutEdit] = useState<(() => void) | null>(null);
  const [showPaneList, setShowPaneList] = useState(false);
  const [onResetToDefault, setOnResetToDefault] = useState<(() => void) | null>(null);

  return (
    <ExpandedMachineContext.Provider
      value={{
        expandedMachine,
        layoutEditMode,
        setExpandedMachine,
        setLayoutEditMode,
        onCollapse,
        setOnCollapse,
        onToggleLayoutEdit,
        setOnToggleLayoutEdit,
        showPaneList,
        setShowPaneList,
        onResetToDefault,
        setOnResetToDefault,
      }}
    >
      {children}
    </ExpandedMachineContext.Provider>
  );
};

export const useExpandedMachine = () => {
  const context = useContext(ExpandedMachineContext);
  if (context === undefined) {
    throw new Error('useExpandedMachine must be used within an ExpandedMachineProvider');
  }
  return context;
};
