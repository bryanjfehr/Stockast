import React, { createContext, useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { jwtDecode } from 'jwt-decode';
import * as authApi from '../api/authApi';

// 1. Create the context object
export const AuthContext = createContext(null);

// 2. Create the provider component
export const AuthProvider = ({ children }) => {
    // State variables
    const [token, setToken] = useState(null);
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Effect to check for a token in localStorage on initial load
    useEffect(() => {
        setLoading(true);
        try {
            const storedToken = localStorage.getItem('token');
            if (storedToken) {
                const decodedUser = jwtDecode(storedToken);

                // Check if the token is expired
                if (decodedUser.exp * 1000 < Date.now()) {
                    // Token is expired, perform logout
                    localStorage.removeItem('token');
                } else {
                    // Token is valid, set auth state
                    setToken(storedToken);
                    setUser(decodedUser);
                    setIsAuthenticated(true);
                }
            }
        } catch (err) {
            console.error('Invalid token found in localStorage:', err);
            // Clear potentially invalid token
            localStorage.removeItem('token');
        } finally {
            setLoading(false);
        }
    }, []);

    // Effect to set the default Authorization header for axios
    useEffect(() => {
        if (token) {
            axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        } else {
            delete axios.defaults.headers.common['Authorization'];
        }
    }, [token]);

    // Login function
    const login = async (email, password) => {
        setLoading(true);
        setError(null);
        try {
            const response = await authApi.login(email, password);
            const accessToken = response.access_token;
            localStorage.setItem('token', accessToken);
            const decodedUser = jwtDecode(accessToken);
            setToken(accessToken);
            setUser(decodedUser);
            setIsAuthenticated(true);
            return true;
        } catch (err) {
            console.error('Login error:', err);
            const errorMessage = err.response?.data?.detail || 'Login failed. Please check your credentials.';
            setError(errorMessage);
            // Ensure auth state is cleared on failed login
            logout();
            return false;
        } finally {
            setLoading(false);
        }
    };

    // Register function
    const register = async (email, password) => {
        setLoading(true);
        setError(null);
        try {
            await authApi.register(email, password);
            return true;
        } catch (err) {
            console.error('Registration error:', err);
            const errorMessage = err.response?.data?.detail || 'Registration failed. Please try again.';
            setError(errorMessage);
            return false;
        } finally {
            setLoading(false);
        }
    };

    // Logout function
    const logout = () => {
        setToken(null);
        setUser(null);
        setIsAuthenticated(false);
        localStorage.removeItem('token');
        // The useEffect hook for the token will handle this, but explicit removal is safer.
        delete axios.defaults.headers.common['Authorization'];
    };

    // Memoize the context value to prevent unnecessary re-renders
    const authContextValue = useMemo(() => ({
        token,
        user,
        isAuthenticated,
        loading,
        error,
        login,
        logout,
        register
    }), [token, user, isAuthenticated, loading, error]);

    // Render the provider with the context value
    return (
        <AuthContext.Provider value={authContextValue}>
            {children}
        </AuthContext.Provider>
    );
};
