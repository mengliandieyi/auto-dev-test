import path from 'path';
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

const frontendRoot = process.env.VITEST_FRONTEND_ROOT || path.resolve(__dirname, 'tests/fixtures/mock-frontend');
const reportDir = process.env.VITEST_REPORT_DIR || path.resolve(__dirname, 'reports/project-a');
const projectId = process.env.VITEST_PROJECT_ID;
const prdId = process.env.VITEST_PRD_ID;
const singleThread = process.env.VITEST_SINGLE_THREAD === '1';

function resolveInclude(): string[] {
  if (projectId && prdId) {
    return [`tests/generated/${projectId}/component/${prdId}_*.test.tsx`];
  }
  if (projectId) {
    return [`tests/generated/${projectId}/component/**/*.test.tsx`];
  }
  return ['tests/generated/**/component/**/*.test.tsx'];
}

function resolveMaxWorkers(): number {
  const raw = process.env.VITEST_MAX_WORKERS;
  if (!raw) return 2;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 2;
}

const poolConfig = singleThread
  ? { poolOptions: { threads: { singleThread: true } } }
  : {
      pool: 'forks' as const,
      poolOptions: { forks: { isolate: true } },
      minWorkers: 1,
      maxWorkers: resolveMaxWorkers(),
    };

export default defineConfig({
  plugins: [react()],
  test: {
    ...poolConfig,
    setupFiles: ['./vitest.setup.ts'],
    include: resolveInclude(),
    environment: 'jsdom',
    globals: true,
    reporters: [
      'default',
      ['json', { outputFile: path.join(reportDir, 'vitest-results.json') }],
    ],
  },
  resolve: {
    alias: {
      '@': path.join(frontendRoot, 'src'),
    },
  },
});
