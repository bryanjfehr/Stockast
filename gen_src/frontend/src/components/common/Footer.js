import React from 'react';

/**
 * Renders the static application footer.
 * Displays the copyright notice with the current year.
 */
const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="app-footer" style={footerStyles.container}>
      <p style={footerStyles.text}>
        &copy; {currentYear} Stockast. All rights reserved.
      </p>
    </footer>
  );
};

// Basic styling to ensure the footer is visible and at the bottom.
// In a larger application, this would likely be in a separate CSS/SCSS file.
const footerStyles = {
  container: {
    textAlign: 'center',
    padding: '20px',
    marginTop: 'auto', // Helps push footer to bottom in a flex layout
    backgroundColor: '#f8f9fa',
    borderTop: '1px solid #e7e7e7',
    color: '#6c757d',
  },
  text: {
    margin: 0,
  },
};

export default Footer;
