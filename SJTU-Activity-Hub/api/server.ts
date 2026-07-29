/**
 * local server entry file, for local development
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import app from './app.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 生产模式：serve 前端构建产物
const distPath = path.resolve(__dirname, '..', 'dist');
app.use(express.static(distPath));
app.get(/^(?!\/api).*/, (_req, res) => {
  res.sendFile(path.join(distPath, 'index.html'));
});

/**
 * start server with port
 */
const PORT = process.env.PORT || 3001;
// reload-trigger: dotenv reads .env in app.ts

const server = app.listen(PORT, () => {
  console.log(`Server ready on port ${PORT}`);
  console.log(`DeepSeek API Key ${process.env.DEEPSEEK_API_KEY ? '已配置' : '未配置'}`);
});

/**
 * close server
 */
process.on('SIGTERM', () => {
  console.log('SIGTERM signal received');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT signal received');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

export default app;