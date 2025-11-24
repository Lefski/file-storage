import React from 'react'
import InputField from '../../components/ui_components/search-bar/InputFiled'
import Button from '../../components/ui_components/button/Button'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom';
import { login } from '../../api/services';

export default function SignInForm() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const navigate = useNavigate();

    async function handleLogin(e) {
        e.preventDefault();
        setError("");
        try {
            await login(email, password);
            navigate("/main");
        } catch (err) {
            setError(err.message);
        }
    }
    return (
        <form className="form" onSubmit={handleLogin}>
            
            <InputField
                className='email'
                type='email'
                placeholder=" Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
            />

            <InputField
                className='password'
                type='password'
                placeholder=" Пароль"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
            />

            {error && <label className="error">{error}</label>}

            <Button type="submit">
                Войти
            </Button>
        </form>
  )
}
