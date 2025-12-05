import React from 'react';
import { Svg, Rect } from 'react-native-svg';

// Placeholder for a single bar in a histogram
const Bar: React.FC = () => {
  return (
    <Svg height="100" width="50">
      <Rect x="5" y="20" width="40" height="80" fill="green" />
    </Svg>
  );
};

export default Bar;