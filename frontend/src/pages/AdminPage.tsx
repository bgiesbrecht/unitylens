import { useState } from 'react';
import { RefreshCw, Play, AlertCircle, CheckCircle } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { getSources, triggerCrawl, getSourceStatus } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { DataTable } from '../components/DataTable';
import { Skeleton } from '../components/Skeleton';
import type { Source, SourceStatus } from '../types';

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

      {toast && <div className={`toast ${toast.type}`}>{toast.message}</div>}
    </div>
  );
}
