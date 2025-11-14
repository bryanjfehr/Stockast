import React from 'react';
import { useNavigate } from 'react-router-dom';
import ApiKeyInput from '../components/settings/ApiKeyInput';
import { useAuth } from '../hooks/useAuth';

/**
 * SettingsPage component allows users to configure their settings,
 * such as updating their Vertex AI API key, and to log out.
 */
const SettingsPage = () => {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  /**
   * Handles the user logout process.
   * It calls the logout function from the auth context to clear authentication state,
   * and then redirects the user to the login page.
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
    <div className="settings-page-container" style={{ padding: '2rem' }}>
      <h2>User Settings</h2>
      
      <div className="user-profile-section" style={{ margin: '2rem 0' }}>
        {user ? (
          <p>Logged in as: <strong>{user.email}</strong></p>
        ) : (
          <p>Loading user information...</p>
        )}
      </div>

      <div className="api-key-section" style={{ marginBottom: '2rem' }}>
        <ApiKeyInput />
      </div>

      <button 
        onClick={handleLogout} 
        className="logout-button"
        style={{ 
          padding: '10px 20px', 
          backgroundColor: '#dc3545', 
          color: 'white', 
          border: 'none', 
          borderRadius: '5px', 
          cursor: 'pointer' 
        }}
      >
        Logout
      </button>
    </div>
  );
};

export default SettingsPage;
