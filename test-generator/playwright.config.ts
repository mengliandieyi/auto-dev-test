import { defineConfig, devices } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const repoRoot = path.join(__dirname, '..');
const reportDir = process.env.PLAYWRIGHT_REPORT_DIR || path.join(repoRoot, 'reports/project-a');

type RuntimeProject = {
  name: string;
  testDir: string;
  baseURL: string;
  webServer?: {
    command: string;
    url: string;
    reuseExistingServer: boolean;
  };
};

function defaultProjects(): RuntimeProject[] {
  return [
    {
      name: 'project-a',
      testDir: 'tests/generated/project-a/e2e',
      baseURL: 'http://127.0.0.1:4173',
      webServer: {
        command: 'npx serve tests/fixtures/mock-e2e -l 4173',
        url: 'http://127.0.0.1:4173/',
        reuseExistingServer: !process.env.CI,
      },
    },
    {
      name: 'project-b',
      testDir: 'tests/generated/project-b/e2e',
      baseURL: 'http://127.0.0.1:4174',
    },
  ];
}

function loadRuntimeProjects(): RuntimeProject[] {
  const runtimePath = path.join(__dirname, 'playwright.runtime.json');
  if (!fs.existsSync(runtimePath)) {
    return defaultProjects();
  }
  try {
    const data = JSON.parse(fs.readFileSync(runtimePath, 'utf-8')) as { projects?: RuntimeProject[] };
    return data.projects?.length ? data.projects : defaultProjects();
  } catch {
    return defaultProjects();
  }
}

function envBaseUrl(projectName: string, fallback: string): string {
  const key = `PROJECT_${projectName.toUpperCase().replace(/-/g, '_')}_BASE_URL`;
  return process.env[key] || fallback;
}

const runtimeProjects = loadRuntimeProjects();
const activeName = process.env.PLAYWRIGHT_ACTIVE_PROJECT || runtimeProjects[0]?.name;
const activeProject = runtimeProjects.find((p) => p.name === activeName) || runtimeProjects[0];

export default defineConfig({
  testDir: path.join(repoRoot, 'tests/generated'),
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,

  reporter: [
    ['list'],
    ['json', { outputFile: path.join(reportDir, 'pw-results.json') }],
  ],

  webServer: activeProject?.webServer
    ? {
        command: activeProject.webServer.command,
        url: activeProject.webServer.url,
        reuseExistingServer: activeProject.webServer.reuseExistingServer,
        cwd: repoRoot,
      }
    : undefined,

  use: {
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },

  projects: runtimeProjects.map((p) => ({
    name: p.name,
    testDir: path.join(repoRoot, p.testDir),
    use: {
      ...devices['Desktop Chrome'],
      baseURL: envBaseUrl(p.name, p.baseURL),
      actionTimeout: 30_000,
      navigationTimeout: 60_000,
    },
  })),
});
