import React from 'react';
import { Svg, Rect } from 'react-native-svg';

// Placeholder for the chart background with grid lines
const ChartBackground: React.FC = () => {
  return (
    <Svg height="100%" width="100%">
      <Rect width="100%" height="100%" fill="#1e1e1e" />
    </Svg>
  );
};

export default ChartBackground;