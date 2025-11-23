import './InputField.css'
const InputField = ({
  inputType = "text",
  value,
  onChange,
  placeholder = "",
  className = "",
  ...props
}) => {
  return (
    <label className={`input-wrapper ${className}`}>
      <input
        className='input-field'
        type={inputType} 
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        {...props}
      />
    </label>
  );
};

export default InputField;