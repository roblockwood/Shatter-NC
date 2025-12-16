import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

const BETA_MODE_KEY = 'shatter_beta_mode';

interface BetaModeContextType {
  isBetaMode: boolean;
  activateBetaMode: () => void;
  deactivateBetaMode: () => void;
}

const BetaModeContext = createContext<BetaModeContextType | undefined>(undefined);

export const BetaModeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isBetaMode, setIsBetaMode] = useState<boolean>(() => {
    // Initialize from localStorage
    const stored = localStorage.getItem(BETA_MODE_KEY);
    return stored === 'true';
  });

  // Persist to localStorage when beta mode changes
  useEffect(() => {
    localStorage.setItem(BETA_MODE_KEY, String(isBetaMode));
  }, [isBetaMode]);

  const activateBetaMode = () => {
    setIsBetaMode(true);
  };

  const deactivateBetaMode = () => {
    setIsBetaMode(false);
    localStorage.removeItem(BETA_MODE_KEY);
  };

  return (
    <BetaModeContext.Provider value={{ isBetaMode, activateBetaMode, deactivateBetaMode }}>
      {children}
    </BetaModeContext.Provider>
  );
};

export const useBetaModeContext = (): BetaModeContextType => {
  const context = useContext(BetaModeContext);
  if (context === undefined) {
    throw new Error('useBetaModeContext must be used within a BetaModeProvider');
  }
  return context;
};

