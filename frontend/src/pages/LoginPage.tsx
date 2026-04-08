import { useState, useEffect } from 'react';
import { ScanSearch, LogIn } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { getVersion } from '../api/client';

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [version, setVersion] = useState('');

  useEffect(() => {
    getVersion().then(setVersion).catch(() => setVersion(''));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? 'Invalid username or password'
          : 'Login failed',
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'var(--bg-secondary, #f5f7fa)',
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: 380,
          padding: 32,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            marginBottom: 24,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <ScanSearch size={22} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.15rem' }}>UnityLens</div>
            <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>Sign in to continue</div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 14 }}>
            <label
              style={{ display: 'block', fontSize: '0.8rem', marginBottom: 4, fontWeight: 500 }}
            >
              Username
            </label>
            <input
              type="text"
              autoFocus
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '9px 12px',
                border: '1px solid var(--border, #d8dde6)',
                borderRadius: 6,
                fontSize: '0.9rem',
              }}
            />
          </div>
          <div style={{ marginBottom: 18 }}>
            <label
              style={{ display: 'block', fontSize: '0.8rem', marginBottom: 4, fontWeight: 500 }}
            >
              Password
            </label>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '9px 12px',
                border: '1px solid var(--border, #d8dde6)',
                borderRadius: 6,
                fontSize: '0.9rem',
              }}
            />
          </div>

          {error && (
            <div
              style={{
                background: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#b91c1c',
                padding: '8px 12px',
                borderRadius: 6,
                fontSize: '0.8rem',
                marginBottom: 14,
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
            style={{ width: '100%', justifyContent: 'center' }}
          >
            {submitting ? (
              <span className="spinner spinner-sm" />
            ) : (
              <LogIn size={15} />
            )}
            Sign in
          </button>
        </form>

        <div
          style={{
            marginTop: 20,
            fontSize: '0.72rem',
            textAlign: 'center',
            opacity: 0.55,
          }}
        >
          UnityLens{version ? ` v${version}` : ''}
        </div>
      </div>
    </div>
  );
}
