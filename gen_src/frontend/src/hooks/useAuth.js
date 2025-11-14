import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';

/**
 * Custom hook for accessing authentication context.
 * This hook provides an easy way to get the auth state and functions
 * from anywhere within the AuthProvider tree.
 *
 * @returns {object} The authentication context value.
 * @throws {Error} If used outside of an AuthProvider.
 */
export const useAuth = () => {
  const context = useContext(AuthContext);

  if (context === undefined) {
    // The context being undefined is a developer error.
    // It means a component is trying to access the auth context
    // without being a descendant of AuthProvider.
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
};
