import { Page, BrowserContext } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

export interface ProjectConfig {
  project_id: string;
  base_url: string;
  auth: {
    type: 'cookie' | 'token' | 'basic' | 'none';
    login_url?: string;
    credentials_env?: string;   // 环境变量前缀，实际值从 process.env 读取
    token_env?: string;
    storage_state_path?: string; // 缓存 cookie 状态，避免每次重复登录
  };
}

/**
 * AuthHelper — 统一鉴权处理
 * 支持 cookie（表单登录）、token（Bearer）、basic auth 三种模式。
 * 凭据全部从环境变量读取，不允许硬编码。
 */
export class AuthHelper {

  /**
   * 主入口：根据项目配置自动完成鉴权
   */
  static async setupAuth(page: Page, context: BrowserContext, config: ProjectConfig) {
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
      case 'none':
      default:
        // 无需鉴权
        break;
    }
  }

  /**
   * Cookie 鉴权：通过表单登录，复用 storageState 缓存会话
   */
  private static async setupCookieAuth(
    page: Page,
    context: BrowserContext,
    config: ProjectConfig
  ) {
    const statePath = config.auth.storage_state_path
      || `tests/intermediate/${config.project_id}/.auth-state.json`;

    // 如果已有缓存的会话状态，直接复用
    if (fs.existsSync(statePath)) {
      await context.addCookies(
        JSON.parse(fs.readFileSync(statePath, 'utf-8')).cookies || []
      );
      return;
    }

    const envPrefix = config.auth.credentials_env || config.project_id.toUpperCase();
    const username = process.env[`${envPrefix}_USER`];
    const password = process.env[`${envPrefix}_PASS`];

    if (!username || !password) {
      throw new Error(
        `Cookie 鉴权失败：缺少环境变量 ${envPrefix}_USER 或 ${envPrefix}_PASS`
      );
    }

    const baseUrl = process.env[`${config.project_id.toUpperCase()}_BASE_URL`]
      || config.base_url;

    await page.goto(`${baseUrl}${config.auth.login_url || '/login'}`);
    await page.getByTestId('username-input').fill(username);
    await page.getByTestId('password-input').fill(password);
    await page.getByTestId('login-btn').click();
    await page.waitForLoadState('networkidle');

    // 缓存会话状态
    const storageDir = path.dirname(statePath);
    if (!fs.existsSync(storageDir)) {
      fs.mkdirSync(storageDir, { recursive: true });
    }
    await context.storageState({ path: statePath });
  }

  /**
   * Token 鉴权：在请求头注入 Bearer token
   */
  private static async setupTokenAuth(page: Page, config: ProjectConfig) {
    const tokenEnv = config.auth.token_env
      || `${config.project_id.toUpperCase()}_TOKEN`;
    const token = process.env[tokenEnv];

    if (!token) {
      throw new Error(`Token 鉴权失败：缺少环境变量 ${tokenEnv}`);
    }

    await page.setExtraHTTPHeaders({
      Authorization: `Bearer ${token}`,
    });
  }

  /**
   * Basic Auth：在请求 URL 中注入凭据（适合简单内网环境）
   */
  private static async setupBasicAuth(page: Page, config: ProjectConfig) {
    const envPrefix = config.auth.credentials_env
      || config.project_id.toUpperCase();
    const username = process.env[`${envPrefix}_USER`];
    const password = process.env[`${envPrefix}_PASS`];

    if (!username || !password) {
      throw new Error(
        `Basic 鉴权失败：缺少环境变量 ${envPrefix}_USER 或 ${envPrefix}_PASS`
      );
    }

    // Playwright 原生支持通过 context 级别的 httpCredentials 处理 Basic Auth
    // 此处以 header 方式兜底
    const encoded = Buffer.from(`${username}:${password}`).toString('base64');
    await page.setExtraHTTPHeaders({
      Authorization: `Basic ${encoded}`,
    });
  }

  /**
   * 清除缓存的会话状态（强制重新登录）
   */
  static clearAuthState(config: ProjectConfig) {
    const statePath = config.auth.storage_state_path
      || `tests/intermediate/${config.project_id}/.auth-state.json`;
    if (fs.existsSync(statePath)) {
      fs.unlinkSync(statePath);
    }
  }
}
