import React, { useState } from 'react';
import { updateSettings } from '../../api/settingsApi';
import { useAuth } from '../../hooks/useAuth';

/**
 * ApiKeyInput component provides a form for users to submit or update their Vertex AI API key.
 * It handles the form submission, API call, and displays success or error messages.
 */
const ApiKeyInput = () => {
    // State for the API key input field
    const [apiKey, setApiKey] = useState('');
    // State to manage loading during API call
    const [loading, setLoading] = useState(false);
    // State to store any error messages from the API call
    const [error, setError] = useState(null);
    // State to store a success message after a successful update
    const [successMessage, setSuccessMessage] = useState(null);

    // Hook to get the authentication token
    const { token } = useAuth();

    /**
     * Handles the form submission.
     * @param {React.FormEvent<HTMLFormElement>} event - The form submission event.
     */
    const handleSubmit = async (event) => {
        event.preventDefault();

        // Clear previous messages
        setError(null);
        setSuccessMessage(null);
        setLoading(true);

        if (!token) {
            setError('Authentication error. Please log in again.');
            setLoading(false);
            return;
        }

        try {
            const settingsData = { vertex_ai_api_key: apiKey };
            const response = await updateSettings(settingsData, token);
            setSuccessMessage(response.message || 'API Key updated successfully!');
            // Clear the input field on success
            setApiKey('');
        } catch (err) {
            console.error('Error updating API key:', err);
            // Extract a user-friendly error message from the server response
            const errorMessage = err.response?.data?.detail || 'Failed to update API key. Please try again.';
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="api-key-input-container">
            <h3>Vertex AI API Key</h3>
            <p>Provide your Vertex AI API key to enable AI-powered features.</p>
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label htmlFor="api-key">API Key:</label>
                    <input
                        id="api-key"
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder="Enter your Vertex AI API Key"
                        required
                        disabled={loading}
                        style={{ marginLeft: '8px', minWidth: '300px' }}
                    />
                </div>
                <button type="submit" disabled={loading} style={{ marginTop: '10px' }}>
                    {loading ? 'Updating...' : 'Update API Key'}
                </button>
            </form>
            {error && <p style={{ color: 'red', marginTop: '10px' }}>{error}</p>}
            {successMessage && <p style={{ color: 'green', marginTop: '10px' }}>{successMessage}</p>}
        </div>
    );
};

export default ApiKeyInput;
