// TODO: make this dynamic between dev and prod
export const BASE_ENDPOINT = window._env_?.API_URL || "http://localhost:8000";
console.log(window._env_)