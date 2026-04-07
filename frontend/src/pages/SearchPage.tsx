import { useState, useEffect } from 'react';
import { Search, ArrowRight } from 'lucide-react';
import { search as searchApi } from '../api/client';
import { CardSkeleton } from '../components/Skeleton';
import { EmptyState } from '../components/EmptyState';
import { useRouter } from '../router';
import type { SearchResult } from '../types';

const EXAMPLE_QUERIES = [
  'Show me all tables related to patient data',
  'What sources contain financial records?',
  'Find tables with email columns',
  'List all schemas in the production catalog',
  'Which tables have timestamp columns?',
];

export function SearchPage() {
  const { path } = useRouter();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  // Parse ?q= from URL
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    const qIdx = hash.indexOf('?');
    if (qIdx >= 0) {
      const sp = new URLSearchParams(hash.slice(qIdx + 1));
      const q = sp.get('q');
      if (q) {
        setQuery(q);
        executeSearch(q);
      }
    }
  }, [path]);

  const executeSearch = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const data = await searchApi(q.trim());
      setResults(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(query);
  };

  const handleExample = (q: string) => {
    setQuery(q);
    executeSearch(q);
  };

  const { navigate } = useRouter();

  return (
    <div>
      <div className="search-hero">
        <h1 className="search-hero-title">Search Your Data Catalog</h1>
        <p className="search-hero-subtitle">
          Ask natural language questions about tables, columns, and schemas across all sources
        </p>

        <form onSubmit={handleSubmit}>
          <div className="search-input-large-wrapper">
            <Search className="search-input-large-icon" />
            <input
              type="text"
              className="search-input-large"
              placeholder="Ask a question about your data catalog..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
            />
            <button type="submit" className="search-input-large-btn" disabled={loading}>
              {loading ? <span className="spinner spinner-sm" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: 'white' }} /> : <ArrowRight size={16} />}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div
          className="card"
          style={{
            maxWidth: 640,
            margin: '0 auto 20px',
            padding: '16px 24px',
            borderColor: 'var(--status-red)',
            background: 'var(--status-red-bg)',
          }}
        >
          <p style={{ color: 'var(--status-red)', fontSize: '0.9rem' }}>{error}</p>
        </div>
      )}

      {loading ? (
        <div className="search-results">
          <CardSkeleton />
          <div style={{ height: 12 }} />
          <CardSkeleton />
          <div style={{ height: 12 }} />
          <CardSkeleton />
        </div>
      ) : searched && results ? (
        results.length > 0 ? (
          <div className="search-results">
            <p style={{
              fontSize: '0.85rem',
              color: 'var(--text-tertiary)',
              marginBottom: 16,
              fontWeight: 500,
            }}>
              {results.length} result{results.length !== 1 ? 's' : ''} found
            </p>
            {results.map((result, i) => (
              <div
                key={i}
                className="card card-clickable search-result-card"
                onClick={() =>
                  navigate(
                    `/browse?source=${encodeURIComponent(result.source)}`
                  )
                }
              >
                <div className="search-result-path">
                  {result.source} / {result.catalog} / {result.schema}
                </div>
                <div className="search-result-name">{result.table}</div>
                {result.description && (
                  <div className="search-result-desc">{result.description}</div>
                )}
                {result.match_reason && (
                  <div className="search-result-reason">{result.match_reason}</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Search size={48} />}
            title="No results found"
            description="Try a different query or browse the catalog directly."
          />
        )
      ) : (
        <div className="search-examples">
          <div className="search-examples-title">Try these example queries</div>
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              className="search-example-item"
              onClick={() => handleExample(q)}
            >
              <Search
                size={14}
                style={{ marginRight: 10, opacity: 0.4, verticalAlign: -2 }}
              />
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
