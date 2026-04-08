import { useEffect, useState } from 'react';
import {
  RefreshCw,
  Play,
  AlertCircle,
  CheckCircle,
  FileText,
  KeyRound,
  Trash2,
  UserPlus,
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import {
  getSources,
  triggerCrawl,
  getSourceStatus,
  listUsers,
  createUser,
  adminResetPassword,
  deleteUser,
  type ManagedUser,
} from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { DataTable } from '../components/DataTable';
import { Skeleton } from '../components/Skeleton';
import type { Source, SourceStatus, CrawlLogEntry } from '../types';

function formatTime(t?: string) {
  if (!t) return 'Never';
  try {
    return new Date(t).toLocaleString();
  } catch {
    return t;
  }
}

export function AdminPage() {
  const { data: sources, loading, refetch } = useApi(getSources);
  const [crawling, setCrawling] = useState<Record<string, boolean>>({});
  const [crawlAll, setCrawlAll] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [healthResults, setHealthResults] = useState<Record<string, SourceStatus>>({});
  const [checkingHealth, setCheckingHealth] = useState<Record<string, boolean>>({});
  const [logsForSource, setLogsForSource] = useState<string | null>(null);
  const [logEntries, setLogEntries] = useState<CrawlLogEntry[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  // ----- User management state -----
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<'admin' | 'viewer'>('viewer');
  const [resetFor, setResetFor] = useState<string | null>(null);
  const [resetPassword, setResetPassword] = useState('');

  const refreshUsers = async () => {
    setUsersLoading(true);
    try {
      setUsers(await listUsers());
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to load users', 'error');
    } finally {
      setUsersLoading(false);
    }
  };

  useEffect(() => {
    refreshUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createUser(newUsername.trim(), newPassword, newRole);
      showToast(`Created user '${newUsername}'`, 'success');
      setNewUsername('');
      setNewPassword('');
      setNewRole('viewer');
      refreshUsers();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Create failed', 'error');
    }
  };

  const handleResetPassword = async (username: string) => {
    if (!resetPassword || resetPassword.length < 4) {
      showToast('Password must be at least 4 characters', 'error');
      return;
    }
    try {
      await adminResetPassword(username, resetPassword);
      showToast(`Password updated for '${username}'`, 'success');
      setResetFor(null);
      setResetPassword('');
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Reset failed', 'error');
    }
  };

  const handleDeleteUser = async (username: string) => {
    if (!confirm(`Delete user '${username}'? This cannot be undone.`)) return;
    try {
      await deleteUser(username);
      showToast(`Deleted user '${username}'`, 'success');
      refreshUsers();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Delete failed', 'error');
    }
  };

  const handleViewLogs = async (name: string) => {
    setLogsForSource(name);
    setLoadingLogs(true);
    try {
      const status = await getSourceStatus(name);
      setLogEntries(status.crawl_log || []);
    } catch {
      setLogEntries([]);
    } finally {
      setLoadingLogs(false);
    }
  };

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleCrawlAll = async () => {
    setCrawlAll(true);
    try {
      const result = await triggerCrawl();
      showToast(result.message || 'Crawl triggered for all sources', 'success');
      setTimeout(refetch, 2000);
    } catch (err: unknown) {
      showToast(
        err instanceof Error ? err.message : 'Failed to trigger crawl',
        'error'
      );
    } finally {
      setCrawlAll(false);
    }
  };

  const handleCrawlSource = async (name: string) => {
    setCrawling((prev) => ({ ...prev, [name]: true }));
    try {
      const result = await triggerCrawl(name);
      showToast(result.message || `Crawl triggered for ${name}`, 'success');
      setTimeout(refetch, 2000);
    } catch (err: unknown) {
      showToast(
        err instanceof Error ? err.message : `Failed to crawl ${name}`,
        'error'
      );
    } finally {
      setCrawling((prev) => ({ ...prev, [name]: false }));
    }
  };

  const handleHealthCheck = async (name: string) => {
    setCheckingHealth((prev) => ({ ...prev, [name]: true }));
    try {
      const status = await getSourceStatus(name);
      setHealthResults((prev) => ({ ...prev, [name]: status }));
    } catch {
      setHealthResults((prev) => ({
        ...prev,
        [name]: { name, status: 'error', message: 'Health check failed' },
      }));
    } finally {
      setCheckingHealth((prev) => ({ ...prev, [name]: false }));
    }
  };

  const tableColumns = [
    { key: 'name', header: 'Source Name' },
    {
      key: 'type',
      header: 'Type',
      render: (row: Source) => (
        <span style={{ textTransform: 'capitalize' as const }}>{row.type}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: Source) => <StatusBadge status={row.status || 'unknown'} />,
    },
    {
      key: 'last_crawled',
      header: 'Last Crawled',
      render: (row: Source) => (
        <span className="crawl-time">{formatTime(row.last_crawled)}</span>
      ),
    },
    {
      key: 'health',
      header: 'Health Check',
      render: (row: Source) => {
        const health = healthResults[row.name];
        const checking = checkingHealth[row.name];
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                handleHealthCheck(row.name);
              }}
              disabled={checking}
            >
              {checking ? (
                <span className="spinner spinner-sm" />
              ) : (
                <RefreshCw size={12} />
              )}
              Check
            </button>
            {health && (
              <span
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  fontSize: '0.8rem',
                }}
              >
                {health.status === 'connected' || health.status === 'ok' ? (
                  <CheckCircle size={14} style={{ color: 'var(--status-green)' }} />
                ) : (
                  <AlertCircle size={14} style={{ color: 'var(--status-red)' }} />
                )}
                {health.message || health.status}
              </span>
            )}
          </div>
        );
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (row: Source) => (
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            className="btn btn-primary btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              handleCrawlSource(row.name);
            }}
            disabled={crawling[row.name]}
          >
            {crawling[row.name] ? (
              <span className="spinner spinner-sm" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} />
            ) : (
              <Play size={12} />
            )}
            Crawl
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              handleViewLogs(row.name);
            }}
          >
            <FileText size={12} />
            Logs
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-header-title">Administration</h1>
        <p className="page-header-desc">
          Manage crawls, monitor source health, and configure data sources
        </p>
      </div>

      {/* Crawl Actions */}
      <div className="admin-section">
        <h2 className="admin-section-title">Crawl Management</h2>
        <div className="admin-actions">
          <button
            className="btn btn-primary"
            onClick={handleCrawlAll}
            disabled={crawlAll}
          >
            {crawlAll ? (
              <span className="spinner spinner-sm" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} />
            ) : (
              <Play size={15} />
            )}
            Crawl All Sources
          </button>
          <button className="btn btn-secondary" onClick={refetch}>
            <RefreshCw size={15} />
            Refresh Status
          </button>
        </div>
      </div>

      {/* Source Status Table */}
      <div className="admin-section">
        <h2 className="admin-section-title">Source Status</h2>
        <div className="card">
          <div className="card-body" style={{ padding: 0 }}>
            {loading ? (
              <div style={{ padding: 24 }}>
                <Skeleton variant="row" count={4} />
              </div>
            ) : (
              <DataTable
                columns={tableColumns}
                data={(sources || []) as Source[]}
                emptyMessage="No data sources configured"
              />
            )}
          </div>
        </div>
      </div>

      {/* User Management */}
      <div className="admin-section">
        <h2 className="admin-section-title">User Management</h2>
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-body" style={{ padding: 16 }}>
            <form
              onSubmit={handleCreateUser}
              style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}
            >
              <div>
                <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: 2 }}>
                  Username
                </label>
                <input
                  type="text"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  required
                  minLength={1}
                  style={{ padding: '6px 10px', border: '1px solid var(--border, #d8dde6)', borderRadius: 6 }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: 2 }}>
                  Password
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={4}
                  style={{ padding: '6px 10px', border: '1px solid var(--border, #d8dde6)', borderRadius: 6 }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: 2 }}>
                  Role
                </label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as 'admin' | 'viewer')}
                  style={{ padding: '6px 10px', border: '1px solid var(--border, #d8dde6)', borderRadius: 6 }}
                >
                  <option value="viewer">viewer</option>
                  <option value="admin">admin</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary btn-sm">
                <UserPlus size={12} />
                Create User
              </button>
            </form>
          </div>
        </div>

        <div className="card">
          <div className="card-body" style={{ padding: 0 }}>
            {usersLoading ? (
              <div style={{ padding: 24 }}>
                <Skeleton variant="row" count={2} />
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border, #e5e7eb)' }}>
                    <th style={{ padding: '10px 16px', fontSize: '0.78rem' }}>Username</th>
                    <th style={{ padding: '10px 16px', fontSize: '0.78rem' }}>Role</th>
                    <th style={{ padding: '10px 16px', fontSize: '0.78rem' }}>Created</th>
                    <th style={{ padding: '10px 16px', fontSize: '0.78rem' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.user_id} style={{ borderBottom: '1px solid var(--border, #f3f4f6)' }}>
                      <td style={{ padding: '10px 16px', fontWeight: 500 }}>{u.username}</td>
                      <td style={{ padding: '10px 16px' }}>{u.role}</td>
                      <td style={{ padding: '10px 16px', fontSize: '0.8rem', opacity: 0.7 }}>
                        {formatTime(u.created_at)}
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        {resetFor === u.username ? (
                          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                            <input
                              type="password"
                              placeholder="new password"
                              value={resetPassword}
                              onChange={(e) => setResetPassword(e.target.value)}
                              style={{
                                padding: '4px 8px',
                                fontSize: '0.8rem',
                                border: '1px solid var(--border, #d8dde6)',
                                borderRadius: 5,
                              }}
                            />
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => handleResetPassword(u.username)}
                            >
                              Save
                            </button>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => {
                                setResetFor(null);
                                setResetPassword('');
                              }}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', gap: 6 }}>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => {
                                setResetFor(u.username);
                                setResetPassword('');
                              }}
                            >
                              <KeyRound size={12} />
                              Reset Password
                            </button>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleDeleteUser(u.username)}
                            >
                              <Trash2 size={12} />
                              Delete
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                  {users.length === 0 && (
                    <tr>
                      <td colSpan={4} style={{ padding: 24, textAlign: 'center', opacity: 0.6 }}>
                        No users.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Crawl Logs Panel */}
      {logsForSource && (
        <div className="admin-section">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 8,
            }}
          >
            <h2 className="admin-section-title" style={{ margin: 0 }}>
              Crawl Logs — {logsForSource}
            </h2>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleViewLogs(logsForSource)}
                disabled={loadingLogs}
              >
                <RefreshCw size={12} />
                Refresh
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setLogsForSource(null);
                  setLogEntries([]);
                }}
              >
                Close
              </button>
            </div>
          </div>
          <div className="card">
            <div
              className="card-body"
              style={{
                padding: 12,
                minHeight: 240,
                maxHeight: 600,
                overflowY: 'auto',
                fontFamily:
                  'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                fontSize: '0.8rem',
                lineHeight: 1.5,
                background: '#0d1117',
                color: '#e6edf3',
              }}
            >
              {loadingLogs ? (
                <div>Loading logs…</div>
              ) : logEntries.length === 0 ? (
                <div style={{ opacity: 0.7 }}>
                  No log entries yet. Trigger a crawl to populate.
                </div>
              ) : (
                logEntries.map((entry, i) => {
                  const color =
                    entry.level === 'error'
                      ? 'var(--status-red, #f85149)'
                      : entry.level === 'warn'
                      ? 'var(--status-yellow, #d29922)'
                      : 'var(--status-green, #3fb950)';
                  return (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        gap: 10,
                        padding: '2px 0',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      <span style={{ color: '#8b949e' }}>
                        {entry.ts ? new Date(entry.ts).toLocaleTimeString() : ''}
                      </span>
                      <span
                        style={{
                          color,
                          fontWeight: 600,
                          minWidth: 44,
                          textTransform: 'uppercase',
                        }}
                      >
                        {entry.level}
                      </span>
                      <span style={{ flex: 1, color: '#e6edf3' }}>{entry.message}</span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
    </div>
  );
}
