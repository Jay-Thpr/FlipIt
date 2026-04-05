const lt = require('localtunnel');
const fs = require('fs');
const path = require('path');

async function start() {
  const tunnel = await lt({ port: 8000 });
  const envPath = path.join(__dirname, 'frontend', '.env');
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
  console.log('Press Ctrl+C to stop.');
  tunnel.on('close', function() { console.log('Tunnel closed'); process.exit(); });
  tunnel.on('error', function(err) { console.error('Tunnel error:', err); });
}

start().catch(function(e) { console.error(e); process.exit(1); });
