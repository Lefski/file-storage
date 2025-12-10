import api from "./api";

export const getUserData = async () => {
    try {
        const res = await api.get("/api/me"); 
        //console.log(res)
        return res;  
    } catch (err) {
        console.error("Ошибка API:", err);
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
            //console.log(res.data.access_token);
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
        var user_data = {
            email,
            username,
            password
        }
        console.log(user_data);
        
        const res = await api.post("/api/register", user_data);
        //console.log(res);

        if (res.data.access_token) {
            //console.log(res.data.access_token);
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

export const logout = async () => {
    try {
        let refresh_token = localStorage.getItem("refresh_token");
        const res = await api.post("/api/logout", {
            refresh_token
        });
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        console.log(res.data)
        return res.data;  
    } catch (err) {
        console.error("Ошибка API:", err);
    }
}

export const getUserFiles = async () => {
    try {
        const res = await api.get("api/files");
        console.log(res.data);
        return res.data;
    } catch (err) {
        console.error("Ошибка API:", err);
    }
}