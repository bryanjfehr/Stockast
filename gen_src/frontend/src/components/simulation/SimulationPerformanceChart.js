import React from 'react';
import PropTypes from 'prop-types';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

/**
 * Formats a timestamp string (e.g., 'YYYY-MM-DD') for display on the X-axis.
 * @param {string} tickItem - The date string to format.
 * @returns {string} - The formatted date string (e.g., '10/26').
 */
const formatXAxisTick = (tickItem) => {
  // Adding 'T00:00:00' ensures the date is parsed in the local timezone,
  // preventing off-by-one day errors.
  const date = new Date(`${tickItem}T00:00:00`);
  return date.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit' });
};

/**
 * Formats a number as a currency string for the Y-axis and tooltips.
 * @param {number} tickItem - The numeric value to format.
 * @returns {string} - The formatted currency string (e.g., '$1,234.56').
 */
const formatYAxisTick = (tickItem) => {
  if (typeof tickItem !== 'number') return '';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(tickItem);
};

/**
 * A component that displays a line chart visualizing portfolio value over time.
 * @param {{ performanceHistory: Array<{timestamp: string, portfolio_value: number}> }}
 */
const SimulationPerformanceChart = ({ performanceHistory }) => {
  if (!performanceHistory || performanceHistory.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '20px', color: '#6c757d' }}>
        <p>No simulation performance data available.</p>
        <p>Run a simulation to see the performance chart.</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" aspect={3}>
      <LineChart
        data={performanceHistory}
        margin={{
          top: 5,
          right: 30,
          left: 40, // Increased left margin for currency values
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#dee2e6" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatXAxisTick}
          type="category"
          allowDuplicatedCategory={false}
          stroke="#495057"
        />
        <YAxis
          tickFormatter={formatYAxisTick}
          domain={['auto', 'auto']}
          stroke="#495057"
          width={80} // Allocate space for formatted currency labels
        />
        <Tooltip
          formatter={(value) => [
            formatYAxisTick(value),
            'Portfolio Value',
          ]}
          labelFormatter={(label) => {
            const date = new Date(`${label}T00:00:00`);
            return `Date: ${date.toLocaleDateString('en-US', { dateStyle: 'long' })}`;
          }}
          contentStyle={{ 
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            border: '1px solid #dee2e6',
            borderRadius: '0.25rem'
          }}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="portfolio_value"
          name="Portfolio Value"
          stroke="#007BFF"
          strokeWidth={2}
          activeDot={{ r: 8 }}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

SimulationPerformanceChart.propTypes = {
  /**
   * An array of data points, each with a timestamp and portfolio value.
   */
  performanceHistory: PropTypes.arrayOf(
    PropTypes.shape({
      timestamp: PropTypes.string.isRequired,
      portfolio_value: PropTypes.number.isRequired,
    })
  ),
};

SimulationPerformanceChart.defaultProps = {
  performanceHistory: [],
};

export default SimulationPerformanceChart;
