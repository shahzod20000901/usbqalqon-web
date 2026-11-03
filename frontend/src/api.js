import axios from "axios";

export const TOKEN_KEY = "usbq_token";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || "";
    if (error.response?.status === 401 && !url.includes("/api/auth/login")) {
      localStorage.removeItem(TOKEN_KEY);
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export function apiError(error, fallback = "Xatolik yuz berdi") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || "Noto'g'ri qiymat")
      .filter(Boolean)
      .join(". ");
  }
  if (error?.code === "ECONNABORTED") return "Server javob bermadi (timeout)";
  if (!error?.response) return "Serverga ulanib bo'lmadi. API ishlayaptimi?";
  return fallback;
}

export default api;
