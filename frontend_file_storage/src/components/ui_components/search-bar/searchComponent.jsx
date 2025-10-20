import React from 'react'

import React from 'react';

const SearchComponent = () => {
  const searchStyles = {
    container: {
      width: '400px',
      height: '30px',
      borderRadius: '5px',
      border: '1px solid black',
      display: 'flex',
      alignItems: 'center',
      padding: '0 10px',
      fontFamily: 'Arial, sans-serif',
      backgroundColor: 'white'
    },
    icon: {
      marginRight: '8px',
      fontSize: '16px'
    },
    input: {
      border: 'none',
      outline: 'none',
      fontSize: '14px',
      width: '100%',
      background: 'transparent'
    }
  };

  return (
    <label style={searchStyles.container}>
      <span style={searchStyles.icon}>🔍</span>
      <input 
        type="text" 
        placeholder="Поиск" 
        style={searchStyles.input}
      />
    </label>
  );
};

export default SearchComponent;