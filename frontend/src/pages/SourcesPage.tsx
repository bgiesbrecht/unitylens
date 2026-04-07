import { Database, RefreshCw } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { getSources } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { CardSkeleton } from '../components/Skeleton';
import { EmptyState } from '../components/EmptyState';
import { useRouter } from '../router';
import type { Source } from '../types';

function formatTime(t?: string) {
  if (!t) return 'Never';
  try {
    return new Date(t).toLocaleString();
  } catch {
    return t;
  }
}

function getTypeClass(type: string): string {
  switch (type?.toLowerCase()) {
    case 'databricks': return 'databricks';
    case 'snowflake': return 'snowflake';
    case 'oracle': return 'oracle';
    default: return 'default';
  }
}

function getTypeAbbr(type: string): string {
  switch (type?.toLowerCase()) {
    case 'databricks': return 'DB';
    case 'snowflake': return 'SF';
    case 'oracle': return 'ORA';
    default: return 'SRC';
  }
}

export function SourcesPage() {
  const { data: sources, loading, error, refetch } = useApi(getSources);
  const { navigate } = useRouter();

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="page-header-title">Data Sources</h1>
          <p className="page-header-desc">
            Configured data source connections
          </p>
        </div>
        <button className="btn btn-secondary" onClick={refetch}>
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="card" style={{ marginBottom: 20, padding: '16px 24px', borderColor: 'var(--status-red)', background: 'var(--status-red-bg)' }}>
          <p style={{ color: 'var(--status-red)', fontSize: '0.9rem' }}>
            Failed to load sources: {error}
          </p>
        </div>
      )}

      {loading ? (
        <div className="source-grid">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : sources && sources.length > 0 ? (
        <div className="source-grid">
          {sources.map((source: Source) => (
            <div
              key={source.name}
              className="card card-clickable source-card"
              onClick={() => navigate(`/browse?source=${encodeURIComponent(source.name)}`)}
            >
              <div className="source-card-header">
                <div>
                  <div className="source-card-name">{source.name}</div>
                  <div className="source-card-type">{source.type}</div>
                </div>
                <div className={`source-card-type-icon ${getTypeClass(source.type)}`}>
                  {getTypeAbbr(source.type)}
                </div>
              </div>

              <StatusBadge status={source.status || 'unknown'} />

              <div className="source-card-stats">
                <div className="source-card-stat">
                  <span className="source-card-stat-value">
                    {source.catalogs_count ?? '--'}
                  </span>
                  <span className="source-card-stat-label">Catalogs</span>
                </div>
                <div className="source-card-stat">
                  <span className="source-card-stat-value">
                    {source.tables_count ?? '--'}
                  </span>
                  <span className="source-card-stat-label">Tables</span>
                </div>
                <div className="source-card-stat">
                  <span className="source-card-stat-value crawl-time">
                    {formatTime(source.last_crawled)}
                  </span>
                  <span className="source-card-stat-label">Last Crawled</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Database size={48} />}
          title="No sources configured"
          description="Add data sources through the configuration file or Admin panel to begin cataloging."
        />
      )}
    </div>
  );
}
