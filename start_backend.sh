#!/bin/bash
# Start backend + localtunnel in one terminal (for eduroam / NAT networks)
cd "$(dirname "$0")"

# Resolve node and python with explicit paths for Git Bash from CMD
NODE="${NODE:-$(which node 2>/dev/null || echo '/c/Program Files/nodejs/node.exe')}"
PYTHON="${PYTHON:-$(which python 2>/dev/null || echo '/c/Python314/python.exe')}"

# Ensure localtunnel is available
if ! "$NODE" -e "require('localtunnel')" 2>/dev/null; then
    echo "Installing localtunnel..."
    npm install localtunnel
fi

# Kill anything already on port 8000
if command -v lsof &>/dev/null; then
    lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
elif command -v netstat &>/dev/null; then
    netstat -aon 2>/dev/null | grep ":8000.*LISTENING" | awk '{print $NF}' | while read pid; do
        taskkill //F //PID "$pid" 2>/dev/null || true
    done
fi

# Start uvicorn in background
echo "Starting uvicorn on 0.0.0.0:8000 ..."
"$PYTHON" -m uvicorn backend.main:app --port 8000 --host 0.0.0.0 &
UVICORN_PID=$!
trap "kill $UVICORN_PID 2>/dev/null" EXIT

sleep 2

# Start tunnel, capture URL, write to frontend/.env, keep running
"$NODE" -e "
const lt = require('localtunnel');
const fs = require('fs');
const path = require('path');
async function start() {
  const tunnel = await lt({ port: 8000 });
  const envPath = path.join('frontend', '.env');
  fs.writeFileSync(envPath, 'EXPO_PUBLIC_API_URL=' + tunnel.url + '\n');
  console.log('');
  console.log('=========================================');
  console.log('Backend:  http://localhost:8000');
  console.log('Tunnel:   ' + tunnel.url);
  console.log('Written:  frontend/.env');
  console.log('=========================================');
  console.log('');
  console.log('Now run in another terminal:');
  console.log('  cd frontend && npx expo start --tunnel --clear');
  console.log('');
  tunnel.on('close', () => { console.log('Tunnel closed'); process.exit(); });
  tunnel.on('error', (err) => { console.error('Tunnel error:', err); });
}
start().catch(e => { console.error(e); process.exit(1); });
"
