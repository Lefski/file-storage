import React, { useState } from 'react';
import { register } from '../../api/services';
import Logo from '../../components/ui_components/logo/Logo';
import Button from '../../components/ui_components/button/Button';
import SignInForm from './SignInForm';
import SignUpForm from './SignUpForm';
import './Login.css';

export default function Login() {
    const [isLogin, setIsLogin] = useState(true);

    return (
        <div className='main-container'>
            <div className='form-container'>
                <Logo></Logo>

                {isLogin? (<SignInForm/>) : 
                (<SignUpForm/>)}

                <label className='form-label'>
                    {isLogin ? "Не зарегистрированы?" : "Уже есть аккаунт?"}
                </label>
                <Button onClick={() => setIsLogin(!isLogin)}>
                    {isLogin ? "Регистрация" : "Войти"}
                </Button>
            </div>
        </div>
    );
}
