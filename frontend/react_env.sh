# Writes runtime env vars into a JS file that the React app loads
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  API_URL: "${MAIN_DRIVER_URL}"
}
EOF