const explicitBase = process.env.REACT_APP_BASE_ENDPOINT;

const isLocalHost =
    typeof window !== "undefined" &&
    ["localhost", "127.0.0.1"].includes(window.location.hostname);

// Local dev: call backend directly. Deployed web app: use nginx/ingress /api route.
export const BASE_ENDPOINT = explicitBase || (isLocalHost ? "http://localhost:8000" : "/api");
