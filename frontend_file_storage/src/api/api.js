import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Добавляет access token во все запросы
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Обновление access токена при ошибке 401
api.interceptors.response.use(
  (response) => response,

  async (error) => {
    const originalRequest = error.config;

    // Если токен истёк
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refresh = localStorage.getItem("refresh_token");

        if (!refresh) {
          throw new Error("Refresh token not found");
        }

        // Обновление токена
        const res = await axios.post(`${API_BASE_URL}/api/refresh`, {
          refresh_token: refresh,
        });

        const newAccess = res.data.access_token;

        // Сохранить новый токен
        localStorage.setItem("access_token", newAccess);

        // Перезаписать хедер
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;

        // Повторить запрос
        return api(originalRequest);

      } catch (err) {
        console.error("Refresh token invalid or expired");

        // Удаляем токены
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");

        // Редирект на логин
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

export default api;
