import React, { useState } from 'react';
import { startSimulation } from '../../api/simulationApi';
import { useAuth } from '../../hooks/useAuth';

/**
 * A form for users to start a new trading simulation by providing an initial capital amount.
 * @param {object} props - The component props.
 * @param {function(object): void} props.onSimulationStart - Callback function executed when a simulation is successfully started. It receives the simulation data as an argument.
 */
const SimulationSetupForm = ({ onSimulationStart }) => {
  const [initialCapital, setInitialCapital] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const { token } = useAuth();

  /**
   * Handles the form submission to start a new simulation.
   * @param {React.FormEvent<HTMLFormElement>} event - The form submission event.
   */
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    const capital = parseFloat(initialCapital);
    if (isNaN(capital) || capital <= 0) {
      setError('Please enter a valid positive number for initial capital.');
      return;
    }

    if (!token) {
      setError('You must be logged in to start a simulation.');
      setLoading(false);
      return;
    }

    setLoading(true);

    try {
      const response = await startSimulation(capital, token);
      if (onSimulationStart) {
        onSimulationStart(response);
      }
      setInitialCapital(''); // Reset form on success
    } catch (err) {
      console.error('Error starting simulation:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to start simulation. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="simulation-setup-form">
      <h2>Start New Simulation</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="initialCapital">Initial Capital ($)</label>
          <input
            id="initialCapital"
            type="number"
            value={initialCapital}
            onChange={(e) => setInitialCapital(e.target.value)}
            placeholder="e.g., 10000"
            required
            min="0.01"
            step="0.01"
            disabled={loading}
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Starting...' : 'Start Simulation'}
        </button>
      </form>
      {loading && <p>Starting simulation...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
    </div>
  );
};

export default SimulationSetupForm;
