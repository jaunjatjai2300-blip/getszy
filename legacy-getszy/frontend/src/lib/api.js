import axios from "axios";
import { _activityInc, _activityDec } from "./requestActivity";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
export const API_BASE = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

export const api = axios.create({ baseURL: API_BASE });

let _refreshing = false;
let _refreshQueue = [];

async function doRefresh() {
  const refreshToken = localStorage.getItem("gs_refresh");
  if (!refreshToken) return false;
  try {
    const { data } = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refreshToken });
    localStorage.setItem("gs_token", data.token);
    localStorage.setItem("gs_refresh", data.refresh);
    return true;
  } catch {
    localStorage.removeItem("gs_token");
    localStorage.removeItem("gs_refresh");
    return false;
  }
}

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("gs_token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  if (cfg.url && API_BASE.replace(/\/+$/, "").endsWith("/api")) {
    cfg.url = cfg.url.replace(/^(\/api)+/, "");
  }
  _activityInc();
  return cfg;
});

api.interceptors.response.use(
  (r) => { _activityDec(); return r; },
  async (err) => {
    _activityDec();
    const original = err.config;
    if (err?.response?.status === 401 && !original._retry) {
      original._retry = true;
      if (!_refreshing) {
        _refreshing = true;
        const ok = await doRefresh();
        _refreshing = false;
        _refreshQueue.forEach((cb) => cb(ok));
        _refreshQueue = [];
        if (ok) {
          original.headers.Authorization = `Bearer ${localStorage.getItem("gs_token")}`;
          return api(original);
        }
      } else {
        return new Promise((resolve, reject) => {
          _refreshQueue.push((ok) => {
            if (ok) {
              original.headers.Authorization = `Bearer ${localStorage.getItem("gs_token")}`;
              resolve(api(original));
            } else {
              reject(err);
            }
          });
        });
      }
    }
    if (err?.response?.status === 401) {
      localStorage.removeItem("gs_token");
      localStorage.removeItem("gs_refresh");
      if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/signup")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export const fmtINR = (n) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n || 0);
