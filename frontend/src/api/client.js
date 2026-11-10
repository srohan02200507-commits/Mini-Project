const API_BASE = import.meta.env.VITE_API_BASE || "/api";

export function getStoredToken() {
  return localStorage.getItem("tradewise_token");
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem("tradewise_token", token);
  } else {
    localStorage.removeItem("tradewise_token");
  }
}

async function request(path, options = {}) {
  const token = getStoredToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = new Error(data.error || `Request failed with status ${response.status}`);
    err.status = response.status;
    err.data = data;
    throw err;
  }
  return data;
}

function toQueryString(params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
  ).toString();
  return qs ? `?${qs}` : "";
}

export const api = {
  // Auth
  register: (payload) => request("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) => request("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request("/auth/me"),

  // Market (Real-Time + Simulated Test Feed)
  getStocks: (data_source = "SIMULATED_TEST") =>
    request(`/market/stocks${toQueryString({ data_source })}`),
  getLiveQuotes: (symbols = "") =>
    request(`/market/live-quotes${toQueryString({ symbols })}`),
  getLiveQuote: (symbol, intraday = true) =>
    request(`/market/live-quote/${encodeURIComponent(symbol)}?intraday=${intraday}`),
  getStockDetail: (symbol, days = 90, data_source = "REAL_MARKET") =>
    request(`/market/stocks/${encodeURIComponent(symbol)}${toQueryString({ days, data_source })}`),
  simulateMarketDay: (days = 1) =>
    request("/market/simulate-day", { method: "POST", body: JSON.stringify({ days }) }),

  // Prediction Accountability Engine
  createPrediction: (payload) =>
    request("/predictions", { method: "POST", body: JSON.stringify(payload) }),
  getPredictions: (params = {}) => request(`/predictions${toQueryString(params)}`),
  getPredictionHistory: (params = {}) => request(`/predictions/history${toQueryString(params)}`),
  getPredictionById: (id) => request(`/predictions/${encodeURIComponent(id)}`),
  verifyPrediction: (id, payload = {}) =>
    request(`/predictions/${encodeURIComponent(id)}/verify`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  verifyDuePredictions: (payload = {}) =>
    request("/predictions/verify-due", { method: "POST", body: JSON.stringify(payload) }),
  getAccountabilityAccuracy: (params = {}) => request(`/predictions/accuracy${toQueryString(params)}`),
  getSymbolComparison: (symbol, data_source = "") =>
    request(`/predictions/comparison/${encodeURIComponent(symbol)}${toQueryString({ data_source })}`),
  getSchedulerStatus: () => request("/predictions/scheduler-status"),

  // Virtual Trading (supports REAL_MARKET live quotes & SIMULATED_TEST)
  getPortfolio: (live = false) => request(`/portfolio${live ? "?live=true" : ""}`),
  getTransactions: (limit = 50) => request(`/portfolio/transactions?limit=${limit}`),
  placeTrade: (payload) => request("/portfolio/trade", { method: "POST", body: JSON.stringify(payload) }),
  resetPortfolio: () => request("/portfolio/reset", { method: "POST" }),

  // Risk & Chat
  getRiskOverview: (symbol = "") => request(`/risk/overview${toQueryString({ symbol })}`),
  getChatHistory: () => request("/chat/history"),
  sendChatMessage: (message, context_symbol = null) =>
    request("/chat/message", {
      method: "POST",
      body: JSON.stringify({ message, context_symbol }),
    }),
  clearChatHistory: () => request("/chat/history", { method: "DELETE" }),
};
