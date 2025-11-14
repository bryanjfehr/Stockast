import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

/**
 * Renders the main navigation bar for the application.
 * Displays different links based on the user's authentication status.
 */
const Navbar = () => {
  // useAuth hook provides authentication state and logout functionality.
  const { isAuthenticated, logout } = useAuth();
  // useNavigate hook for programmatic navigation.
  const navigate = useNavigate();

  /**
   * Handles the user logout process.
   * It calls the logout function from the auth context and then redirects
   * the user to the login page.
   */
  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error("Failed to logout:", error);
      // Optionally, display an error message to the user
    }
  };

  return (
    <nav style={{ display: 'flex', justifyContent: 'space-between', padding: '1rem', borderBottom: '1px solid #ccc', alignItems: 'center' }}>
      <div>
        <Link to="/" style={{ textDecoration: 'none', color: 'black', fontWeight: 'bold', fontSize: '1.5rem' }}>
          Stockast
        </Link>
      </div>
      <div>
        {isAuthenticated ? (
          <>
            <Link to="/" style={{ margin: '0 10px', textDecoration: 'none', color: 'blue' }}>Dashboard</Link>
            <Link to="/simulation" style={{ margin: '0 10px', textDecoration: 'none', color: 'blue' }}>Simulation</Link>
            <Link to="/settings" style={{ margin: '0 10px', textDecoration: 'none', color: 'blue' }}>Settings</Link>
            <button onClick={handleLogout} style={{ margin: '0 10px' }}>Logout</button>
          </>
        ) : (
          <>
            <Link to="/login" style={{ margin: '0 10px', textDecoration: 'none', color: 'blue' }}>Login</Link>
          </>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
