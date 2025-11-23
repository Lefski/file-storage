import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/api'; // импортируем твой axios-инстанс
import './Login.css';
import InputField from '../../components/ui_components/search-bar/InputFiled';
import Logo from '../../components/ui_components/logo/Logo';
import Button from '../../components/ui_components/button/Button';

export default function Login({ onLogin }) {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");

    const navigate = useNavigate();

    async function handleSubmit(e) {
        e.preventDefault();
        setError("");

        const url = isLogin ? "/api/login" : "/api/register";

        try {
            const res = await api.post(url, {
                email,
                password
            });

            // JWT токен из ответа — подстрой под свой бекенд!
            if (res.data.token) {
                localStorage.setItem("token", res.data.token);
            }

            onLogin();      
            navigate("/main");

        } catch (err) {
            if (err.response?.data?.message) {
                setError(err.response.data.message);
            } else {
                setError("Ошибка соединения с сервером");
            }
        }
    }

    return (
        <div className='main-container'>
            <div className='form-container'>
                <Logo></Logo>
                <form className="form" onSubmit={handleSubmit}>
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


                    {error && <p className="error">{error}</p>}

                    <Button type="submit">
                        {isLogin ? "Войти" : "Зарегистрироваться"}
                    </Button>

                    <label className='form-label'>
                        {isLogin ? "Не зарегистрированы?" : "Уже есть аккаунт?"}
                    </label>

                    <Button onClick={() => setIsLogin(!isLogin)}>
                        {isLogin ? "Регистрация" : "Войти"}
                    </Button>
                </form>
            </div>
        </div>
    );
}
