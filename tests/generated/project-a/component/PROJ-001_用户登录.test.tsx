/**
 * AUTO-GENERATED — DO NOT EDIT MANUALLY
 * PRD: PROJ-001 v1.0.0 (project-a)
 * Hash: 9efe329dcd748d46138792c49219da0672d224531d6aae41b270714a13cc6850
 * Layer: component
 * Generated: 2026-06-15T10:36:59.875914+00:00
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../../msw/server';
import LoginForm from '@/components/LoginForm';

describe('用户登录', () => {
  it('CTC-001: 错误密码时 LoginForm 显示错误提示', async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json({"message": "账号或密码错误"}, { status: 401 })
      )
    );
    render(<LoginForm />);
    await user.clear(screen.getByTestId('username-input'));
    await user.type(screen.getByTestId('username-input'), "test@example.com");
    await user.clear(screen.getByTestId('password-input'));
    await user.type(screen.getByTestId('password-input'), "WrongPass!");
    await user.click(screen.getByTestId('login-btn'));
    expect(await screen.findByTestId('error-message')).toHaveTextContent("账号或密码错误");
  });

  it('CTC-002: 账号或密码为空时登录按钮禁用', async () => {
    const user = userEvent.setup();
    render(<LoginForm />);
    await user.clear(screen.getByTestId('username-input'));
    await user.type(screen.getByTestId('username-input'), "test@example.com");
    await user.clear(screen.getByTestId('password-input'));
    await user.type(screen.getByTestId('password-input'), "\"\"");
    expect(screen.getByTestId('login-btn')).toBeDisabled();
  });

  it('CTC-003: 账号被锁定时显示锁定提示', async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json({"message": "账号或密码错误"}, { status: 423 })
      )
    );
    render(<LoginForm />);
    await user.clear(screen.getByTestId('username-input'));
    await user.type(screen.getByTestId('username-input'), "locked@example.com");
    await user.clear(screen.getByTestId('password-input'));
    await user.type(screen.getByTestId('password-input'), "AnyPass1!");
    await user.click(screen.getByTestId('login-btn'));
    expect(await screen.findByTestId('lock-message')).toHaveTextContent("账号已锁定，请 15 分钟后重试");
    expect(screen.getByTestId('login-btn')).toBeDisabled();
  });

});
