import { useState, FormEvent } from 'react';

const VALID_USER = 'test@example.com';
const VALID_PASS = 'Test1234!';

export default function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const canSubmit = username.trim().length > 0 && password.length > 0;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        setError('账号或密码错误');
        setPassword('');
      }
    } catch {
      setError('账号或密码错误');
      setPassword('');
    }
  };

  return (
    <form onSubmit={onSubmit}>
      <input
        data-testid="username-input"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        data-testid="password-input"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button data-testid="login-btn" type="submit" disabled={!canSubmit}>
        登录
      </button>
      {error ? <div data-testid="error-message">{error}</div> : null}
    </form>
  );
}
