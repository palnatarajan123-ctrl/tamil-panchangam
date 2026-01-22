# Tamil Panchangam Engine - Startup Configuration

## Overview

This application runs a **dual-server architecture**:
- **Frontend**: Vite React dev server on port 5000
- **Backend**: Python FastAPI with Uvicorn on port 8000

The frontend proxies `/api` requests to the backend.

---

## Key Configuration Files

### 1. `package.json`

```json
{
  "scripts": {
    "dev": "bash scripts/start-dev.sh",
    "build": "vite build"
  }
}
```

- The `dev` script runs `scripts/start-dev.sh` which starts both servers.

---

### 2. `scripts/start-dev.sh`

This shell script starts both servers in parallel:

```bash
#!/bin/bash

echo "Starting Tamil Panchangam Engine..."

# Start the Python backend
cd tamil_panchangam_engine && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 3

# Start the frontend
cd /home/runner/workspace && npx vite &
FRONTEND_PID=$!

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
```

---

### 3. `vite.config.ts` (Root)

Critical settings for the frontend dev server:

```typescript
server: {
  port: 5000,              // Frontend port (exposed to external port 80)
  host: "0.0.0.0",         // Bind to all interfaces
  strictPort: false,       // Allow fallback ports
  allowedHosts: true,      // CRITICAL: Allow Replit proxy hosts

  proxy: {
    "/api": {
      target: "http://localhost:8000",  // Backend server
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ""),
    },
  },
}
```

**Important**: `allowedHosts: true` is required for Replit's proxy system to work.

---

### 4. `.replit`

Workflow configuration:

```toml
[[ports]]
localPort = 5000
externalPort = 80

[workflows]
runButton = "Project"

[[workflows.workflow]]
name = "Start application"
[[workflows.workflow.tasks]]
task = "shell.exec"
args = "npm run dev"
waitForPort = 5000
```

---

### 5. `tamil_panchangam_engine/app/main.py`

Python FastAPI backend entry point:

- Runs on port 8000
- Serves API routes under `/`
- In production: serves static frontend from `dist/public`

---

## Port Configuration

| Service  | Local Port | External Port | Description |
|----------|------------|---------------|-------------|
| Frontend | 5000       | 80            | Vite dev server |
| Backend  | 8000       | 8000          | Uvicorn API server |

---

## API Proxy

Frontend requests to `/api/*` are proxied to the backend:

```
Frontend: /api/base-chart/list
    ↓ (proxy rewrite)
Backend:  http://localhost:8000/base-chart/list
```

---

## Deployment (Production)

For production deployment, the `.replit` configures:

```toml
[deployment]
run = ["python", "-m", "uvicorn", "tamil_panchangam_engine.app.main:app", "--host", "0.0.0.0", "--port", "5000"]
build = ["npm", "run", "build"]
```

In production:
1. `npm run build` compiles frontend to `dist/public`
2. Uvicorn serves both API and static frontend on port 5000

---

## Troubleshooting

### "Blocked request" error
Ensure `vite.config.ts` has `allowedHosts: true` in the server config.

### "Port already in use" error
Kill existing processes:
```bash
fuser -k 5000/tcp
fuser -k 8000/tcp
```

### Backend not responding
Check if uvicorn is running:
```bash
curl http://localhost:8000/health
```

### Frontend not loading
Check Vite logs in the workflow output and ensure port 5000 is bound.

---

## File Structure

```
workspace/
├── client/                    # React frontend source
│   ├── src/
│   └── index.html
├── tamil_panchangam_engine/   # Python backend
│   └── app/
│       └── main.py           # FastAPI entry point
├── scripts/
│   └── start-dev.sh          # Development startup script
├── vite.config.ts            # Vite configuration (root)
├── package.json              # Node scripts & dependencies
└── .replit                   # Replit workflow config
```

---

## Quick Reference

**Start development:**
- Press the green Run button, OR
- Run `npm run dev`

**Build for production:**
- Run `npm run build`

**Check services:**
- Frontend: http://localhost:5000
- Backend health: http://localhost:8000/health
