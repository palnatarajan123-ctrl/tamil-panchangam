#!/usr/bin/env bash
set -e

echo "🚀 Setting up full-stack (FastAPI + React) in one repo..."

# -------------------------------------------------
# 1. Create frontend using Vite (React + TS)
# -------------------------------------------------
if [ ! -d "client" ]; then
  echo "📦 Creating Vite React frontend..."
  npm create vite@latest client -- --template react-ts
else
  echo "⚠️ client/ already exists, skipping creation"
fi

cd client

echo "📦 Installing frontend dependencies..."
npm install

# -------------------------------------------------
# 2. Install extra UI + tooling deps
# -------------------------------------------------
npm install \
  @tanstack/react-query \
  axios \
  clsx \
  tailwindcss postcss autoprefixer

npx tailwindcss init -p

# -------------------------------------------------
# 3. Configure Tailwind
# -------------------------------------------------
cat > tailwind.config.js <<'EOF'
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

cat > src/index.css <<'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF

# -------------------------------------------------
# 4. Patch Vite config (root + build output)
# -------------------------------------------------
cat > vite.config.ts <<'EOF'
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  root: ".",
  build: {
    outDir: "../dist/public",
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});
EOF

# -------------------------------------------------
# 5. Minimal App.tsx placeholder
# -------------------------------------------------
cat > src/App.tsx <<'EOF'
export default function App() {
  return (
    <div style={{ padding: 24 }}>
      <h1>Tamil Panchangam</h1>
      <p>Frontend is live.</p>
      <p>Backend API: /prediction/monthly</p>
    </div>
  );
}
EOF

# -------------------------------------------------
# 6. Build frontend
# -------------------------------------------------
echo "🏗️ Building frontend..."
npm run build

cd ..

# -------------------------------------------------
# 7. Wire FastAPI to serve frontend
# -------------------------------------------------
MAIN_FILE="app/main.py"

if ! grep -q "StaticFiles" "$MAIN_FILE"; then
  echo "🔌 Wiring FastAPI static serving..."

  sed -i '/from fastapi import FastAPI/a\
from fastapi.staticfiles import StaticFiles\
from fastapi.responses import FileResponse' "$MAIN_FILE"

  sed -i '/app = FastAPI/a\
\n# Serve frontend\napp.mount("/", StaticFiles(directory="dist/public", html=True), name="frontend")\n' "$MAIN_FILE"
else
  echo "⚠️ StaticFiles already wired, skipping"
fi

echo "✅ DONE!"
echo ""
echo "▶️ Run with:"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000"
