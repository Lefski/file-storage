import api from "./api";

export const getUserData = async () => {
    try {
        const res = await api.get("/api/me"); 
        console.log(res.data)
        return res.data;  
    } catch (err) {
        console.error("Ошибка API:", err);
        throw new Error("Ошибка получения данных пользователя");
    }
}

export const login = async (email, password) => {
    try {
        const res = await api.post("/api/login", {
            email,
            password
        });
        //console.log(res);
        if (res.data.access_token) {
            console.log(res.data.access_token);
            localStorage.setItem("access_token", res.data.access_token);
        }
        if (res.data.refresh_token) {
            localStorage.setItem("refresh_token", res.data.refresh_token);
        }
        return res.data;

    } catch (err) {
        //console.log(err);
        if (err.response?.status == "401") {
            throw new Error("Неверный email или пароль!");
        } else {
            throw new Error("Ошибка соединения с сервером");
        }
    }
}

export const register = async (email, username, password) => {
    try {
        const res = await api.post("/api/register", {
            email,
            username,
            password
        });
        //console.log(res);

        if (res.data.access_token) {
            console.log(res.data.access_token);
            localStorage.setItem("access_token", res.data.access_token);
        }
        if (res.data.refresh_token) {
            localStorage.setItem("refresh_token", res.data.refresh_token);
        }

    } catch (err) {
        if (err.response?.data?.message) {
            throw new Error(err.response.data.message);
        } else {
            throw new Error("Ошибка соединения с сервером");
        }
    }
}