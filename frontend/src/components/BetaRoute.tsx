import { Navigate } from 'react-router-dom';
import { useBetaMode } from '../hooks/useBetaMode';
import { ReactNode } from 'react';

interface BetaRouteProps {
  children: ReactNode;
}

/**
 * Route guard component that only renders children when beta mode is active
 * Redirects to dashboard if beta mode is not active
 */
export const BetaRoute: React.FC<BetaRouteProps> = ({ children }) => {
  const { isBetaMode } = useBetaMode();

  if (!isBetaMode) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

