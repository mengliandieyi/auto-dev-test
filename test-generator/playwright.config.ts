import { defineConfig, devices } from '@playwright/test';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const repoRoot = path.join(__dirname, '..');
const reportDir = process.env.PLAYWRIGHT_REPORT_DIR || path.join(repoRoot, 'reports/project-a');
const runtimePath = path.join(__dirname, 'playwright.runtime.json');

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

function ensureRuntimeFile(): void {
  if (fs.existsSync(runtimePath)) return;
  execSync('python3 playwright_runtime.py', { cwd: repoRoot, stdio: 'pipe' });
}

function loadRuntimeProjects(): RuntimeProject[] {
  ensureRuntimeFile();
  const data = JSON.parse(fs.readFileSync(runtimePath, 'utf-8')) as { projects?: RuntimeProject[] };
  if (!data.projects?.length) {
    throw new Error('playwright.runtime.json has no projects; check config/projects/*.yaml');
  }
  return data.projects;
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
