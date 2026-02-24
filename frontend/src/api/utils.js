// Use env var for Docker builds; fallback for local dev (npm start)
export const BASE_ENDPOINT = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000"