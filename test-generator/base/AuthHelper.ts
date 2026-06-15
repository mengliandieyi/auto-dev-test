import { Page, BrowserContext } from '@playwright/test';

export interface ProjectConfig {
  project_id: string;
  base_url: string;
  auth: {
    type: 'cookie' | 'token' | 'basic' | 'none';
    login_url?: string;
    credentials_env?: string;
    token_env?: string;
    storage_state_path?: string;
  };
}

/**
 * AuthHelper — 统一鉴权（TECH §3.5）
 * M1 fixture：cookie / token / basic 均 skip（无真实登录环境）
 * M6 staging：设置 AUTH_MODE=real 启用真实鉴权
 */
export class AuthHelper {
  static async setupAuth(page: Page, context: BrowserContext, config: ProjectConfig) {
    if (process.env.AUTH_MODE !== 'real') {
      return;
    }
    const { type } = config.auth;
    switch (type) {
      case 'cookie':
        await AuthHelper.setupCookieAuth(page, context, config);
        break;
      case 'token':
        await AuthHelper.setupTokenAuth(page, config);
        break;
      case 'basic':
        await AuthHelper.setupBasicAuth(page, config);
        break;
      default:
        break;
    }
  }

  private static async setupCookieAuth(
    page: Page,
    context: BrowserContext,
    config: ProjectConfig,
  ) {
    const envPrefix = config.auth.credentials_env || config.project_id.toUpperCase();
    const username = process.env[`${envPrefix}_USER`];
    const password = process.env[`${envPrefix}_PASS`];
    if (!username || !password) {
      throw new Error(`Cookie 鉴权失败：缺少 ${envPrefix}_USER / _PASS`);
    }
    const baseUrl = process.env[`${config.project_id.toUpperCase()}_BASE_URL`] || config.base_url;
    await page.goto(`${baseUrl}${config.auth.login_url || '/login'}`);
    await page.getByTestId('username-input').fill(username);
    await page.getByTestId('password-input').fill(password);
    await page.getByTestId('login-btn').click();
    await page.waitForLoadState('networkidle');
    const statePath = config.auth.storage_state_path
      || `tests/intermediate/${config.project_id}/.auth-state.json`;
    await context.storageState({ path: statePath });
  }

  private static async setupTokenAuth(page: Page, config: ProjectConfig) {
    const tokenEnv = config.auth.token_env || `${config.project_id.toUpperCase()}_TOKEN`;
    const token = process.env[tokenEnv];
    if (!token) throw new Error(`Token 鉴权失败：缺少 ${tokenEnv}`);
    await page.setExtraHTTPHeaders({ Authorization: `Bearer ${token}` });
  }

  private static async setupBasicAuth(page: Page, config: ProjectConfig) {
    const envPrefix = config.auth.credentials_env || config.project_id.toUpperCase();
    const username = process.env[`${envPrefix}_USER`];
    const password = process.env[`${envPrefix}_PASS`];
    if (!username || !password) {
      throw new Error(`Basic 鉴权失败：缺少 ${envPrefix}_USER / _PASS`);
    }
    const encoded = Buffer.from(`${username}:${password}`).toString('base64');
    await page.setExtraHTTPHeaders({ Authorization: `Basic ${encoded}` });
  }
}
