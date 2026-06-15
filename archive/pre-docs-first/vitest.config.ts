import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

/**
 * Vitest 配置 — 组件测试
 * @testing → tests/（MSW 等共享测试基础设施）
 * VITEST_FRONTEND_ROOT → 业务仓根目录（由 run.py 从 project.yaml vitest.frontend_root 注入）
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['tests/generated/**/component/**/*.test.tsx'],
    globals: true,
    reporters: ['verbose', ['json', { outputFile: 'reports/vitest-results.json' }]],
    poolOptions: { threads: { singleThread: true } },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, process.env.VITEST_FRONTEND_ROOT || '../acme-web', 'src'),
      '@testing': resolve(__dirname, './tests'),
    },
  },
});
