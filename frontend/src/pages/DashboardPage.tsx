import {
  Database,
  BookOpen,
  Layers,
  Table2,
  RefreshCw,
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { getStats, getSources } from '../api/client';
import { Skeleton } from '../components/Skeleton';
import { StatusBadge } from '../components/StatusBadge';
import { SearchBar } from '../components/SearchBar';
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

export function DashboardPage() {
  const { data: stats, loading: statsLoading } = useApi(getStats);
  const { data: sources, loading: sourcesLoading } = useApi(getSources);
  const { navigate } = useRouter();

  return (
    <div>
      <div className="page-header">
        <h1 className="page-header-title">Dashboard</h1>
        <p className="page-header-desc">
          Overview of your unified data catalog
        </p>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <StatCard
          icon={<Database size={20} />}
          color="blue"
          value={stats?.total_sources}
          label="Data Sources"
          loading={statsLoading}
        />
        <StatCard
          icon={<BookOpen size={20} />}
          color="green"
          value={stats?.total_catalogs}
          label="Catalogs"
          loading={statsLoading}
        />
        <StatCard
          icon={<Layers size={20} />}
          color="purple"
          value={stats?.total_schemas}
          label="Schemas"
          loading={statsLoading}
        />
        <StatCard
          icon={<Table2 size={20} />}
          color="orange"
          value={stats?.total_tables}
          label="Tables"
          loading={statsLoading}
        />
      </div>

      {/* Quick Search */}
      <div className="card" style={{ marginBottom: 28 }}>
        <div className="card-body" style={{ textAlign: 'center', padding: '28px 24px' }}>
          <p style={{ marginBottom: 16, color: 'var(--text-secondary)', fontWeight: 500 }}>
            Ask a question about your data catalog
          </p>
          <div style={{ maxWidth: 520, margin: '0 auto' }}>
            <SearchBar placeholder="Search tables, columns, descriptions..." />
          </div>
        </div>
      </div>

      {/* Source Status */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 16 }}>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Source Status</h2>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate('/sources')}
          >
            View All
          </button>
        </div>
        <div className="card-body" style={{ paddingTop: 0 }}>
          {sourcesLoading ? (
            <Skeleton variant="row" count={3} />
          ) : sources && sources.length > 0 ? (
            <div className="activity-list">
              {sources.map((source: Source) => (
                <div
                  key={source.name}
                  className="activity-item"
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate('/sources')}
                >
                  <div
                    className="activity-item-icon"
                    style={{
                      background: getSourceColor(source.type),
                      color: 'white',
                      fontSize: '0.65rem',
                      fontWeight: 700,
                    }}
                  >
                    {getSourceAbbr(source.type)}
                  </div>
                  <div className="activity-item-content">
                    <div className="activity-item-title">{source.name}</div>
                    <div className="activity-item-time">
                      <RefreshCw size={11} style={{ marginRight: 4, verticalAlign: -1 }} />
                      Last crawled: {formatTime(source.last_crawled)}
                    </div>
                  </div>
                  <div className="activity-item-status">
                    <StatusBadge status={source.status || 'unknown'} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--text-tertiary)' }}>
              No sources configured. Add sources in the Admin panel.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  color,
  value,
  label,
  loading,
}: {
  icon: React.ReactNode;
  color: string;
  value?: number;
  label: string;
  loading: boolean;
}) {
  return (
    <div className="stat-card">
      <div className={`stat-card-icon ${color}`}>{icon}</div>
      {loading ? (
        <Skeleton variant="text-lg" />
      ) : (
        <div className="stat-card-value">{value ?? 0}</div>
      )}
      <div className="stat-card-label">{label}</div>
    </div>
  );
}

function getSourceColor(type: string): string {
  switch (type?.toLowerCase()) {
    case 'databricks': return 'linear-gradient(135deg, #ff3621, #ff6a4d)';
    case 'snowflake': return 'linear-gradient(135deg, #29b5e8, #56cdf5)';
    case 'oracle': return 'linear-gradient(135deg, #c74634, #e05a47)';
    default: return 'linear-gradient(135deg, #6366f1, #818cf8)';
  }
}

function getSourceAbbr(type: string): string {
  switch (type?.toLowerCase()) {
    case 'databricks': return 'DB';
    case 'snowflake': return 'SF';
    case 'oracle': return 'ORA';
    default: return 'SRC';
  }
}
