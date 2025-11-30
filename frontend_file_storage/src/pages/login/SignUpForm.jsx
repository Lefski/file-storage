import React from 'react'
import InputField from '../../components/ui_components/search-bar/InputFiled'
import Button from '../../components/ui_components/button/Button'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom';
import { register, login } from '../../api/services';

export default function SignUpForm({handleRegister}) {
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [password2, setPassword2] = useState("");
    const [error, setError] = useState("");
    const navigate = useNavigate();

    async function handleRegister(e) {
        e.preventDefault();
        setError("");

        try {
            if (password == password2) {
                await register(email, username, password);
                await login(email, password)
                navigate("/main");
            } else {
                throw new Error("Пароли не совпадают!")
            }
        } catch (err) {
            setError(err.message);
        }
    }
    return (
        <form className="form" onSubmit={handleRegister}>
            <InputField
                className='email'
                type='text'
                placeholder=" Имя пользователя"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
            />

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

            <InputField
                className='password'
                type='password'
                placeholder=" Повторите пароль"
                value={password2}
                onChange={(e) => setPassword2(e.target.value)}
                required
            />

            {error && <label className="error">{error}</label>}

            <Button type="submit">
                Зарегистрироваться
            </Button>
        </form>
  )
}
