import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, process.cwd(), 'VITE_');
  const port = Number(environment.VITE_DEV_SERVER_PORT ?? 5173);

  if (!Number.isInteger(port) || port <= 0 || port > 65535) {
    throw new Error('VITE_DEV_SERVER_PORT must be a valid TCP port.');
  }

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      port,
      strictPort: true,
    },
    preview: {
      host: '0.0.0.0',
      port,
      strictPort: true,
    },
  };
});
