import type {
  Source,
  Catalog,
  Schema,
  Table,
  SearchResult,
  DashboardStats,
  HealthCheck,
  CrawlResult,
  SourceStatus,
} from '../types';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text().catch(() => 'Unknown error');
    throw new Error(`API error ${response.status}: ${text}`);
  }
  return response.json();
}

export async function getSources(): Promise<Source[]> {
  const raw = await request<any[]>(`${BASE}/sources`);
  return raw.map((s) => ({
    name: s.source_name,
    type: s.source_type,
    status:
      s.last_status === 'success'
        ? 'connected'
        : s.last_status === 'running'
        ? 'crawling'
        : s.last_status === 'error'
        ? 'error'
        : s.last_status === 'connected'
        ? 'connected'
        : s.last_status === 'not_crawled'
        ? 'not_crawled'
        : 'unknown',
    last_crawled: s.last_crawl_at,
    host: s.host,
    crawl_log: Array.isArray(s.crawl_log) ? s.crawl_log : [],
  }));
}

export interface CatalogDetail {
  source_name: string;
  catalog_name: string;
  full_name: string;
  comment: string;
  owner: string;
  schema_count: number;
  table_count: number;
  column_count: number;
}

export async function getCatalogsDetail(source?: string): Promise<CatalogDetail[]> {
  const url = source
    ? `${BASE}/catalogs/detail?source=${encodeURIComponent(source)}`
    : `${BASE}/catalogs/detail`;
  return request<CatalogDetail[]>(url);
}

export async function getCatalogs(source?: string): Promise<Catalog[]> {
  const url = source ? `${BASE}/catalogs?source=${encodeURIComponent(source)}` : `${BASE}/catalogs`;
  const raw = await request<any[]>(url);
  return raw.map((c) => ({
    name: c.catalog_name,
    source: c.source_name,
  }));
}

export async function getSchemas(source: string, catalog: string): Promise<Schema[]> {
  const raw = await request<any[]>(
    `${BASE}/schemas/${encodeURIComponent(source)}/${encodeURIComponent(catalog)}`
  );
  return raw.map((s) => ({
    name: s.schema_name,
    source: s.source_name,
    catalog: s.catalog_name,
  }));
}

export async function getTables(source: string, catalog: string, schema: string): Promise<Table[]> {
  const raw = await request<any[]>(
    `${BASE}/tables/${encodeURIComponent(source)}/${encodeURIComponent(catalog)}/${encodeURIComponent(schema)}`
  );
  return raw.map(mapTable);
}

function mapTable(t: any): Table {
  return {
    name: t.table_name,
    source: t.source_name,
    catalog: t.catalog_name,
    schema: t.schema_name,
    type: t.table_type,
    description: t.comment,
    owner: t.owner,
    columns: t.columns?.map((c: any) => ({
      name: c.column_name,
      type: c.data_type,
      nullable: c.is_nullable === 1 || c.is_nullable === true,
      comment: c.comment,
      position: c.ordinal_position,
    })),
  };
}

export async function getTableDetail(
  source: string,
  catalog: string,
  schema: string,
  table: string
): Promise<Table> {
  const raw = await request<any>(
    `${BASE}/tables/${encodeURIComponent(source)}/${encodeURIComponent(catalog)}/${encodeURIComponent(schema)}/${encodeURIComponent(table)}`
  );
  return mapTable(raw);
}

export async function search(query: string): Promise<SearchResult[]> {
  const raw = await request<any>(`${BASE}/search?q=${encodeURIComponent(query)}`);
  const results = raw.keyword_results || [];
  return results.map((r: any) => {
    const parts = (r.full_name || '').split('::');
    const source = parts[0] || '';
    const path = (parts[1] || '').split('.');
    return {
      source,
      catalog: path[0] || '',
      schema: path[1] || '',
      table: path[2] || '',
      description: r.comment || '',
      match_reason: `${r.object_type || ''}${r.extra ? ' (' + r.extra + ')' : ''}`,
    };
  });
}

export async function triggerCrawl(source?: string): Promise<CrawlResult> {
  const url = source ? `${BASE}/admin/crawl/${encodeURIComponent(source)}` : `${BASE}/admin/crawl`;
  return request<CrawlResult>(url, { method: 'POST' });
}

export async function getSourceStatus(name: string): Promise<SourceStatus> {
  const raw = await request<any>(`${BASE}/admin/sources/${encodeURIComponent(name)}/status`);
  return {
    name: raw.source_name,
    status: raw.last_status,
    message: raw.last_error,
    last_checked: raw.last_crawl_at,
    crawl_log: Array.isArray(raw.crawl_log) ? raw.crawl_log : [],
  };
}

export async function getHealth(): Promise<HealthCheck> {
  return request<HealthCheck>(`${BASE}/health`);
}

export async function getVersion(): Promise<string> {
  const raw = await request<{ version: string }>(`${BASE}/version`);
  return raw.version;
}

export async function getStats(): Promise<DashboardStats> {
  const raw = await request<any>(`${BASE}/stats`);
  return {
    total_sources: raw.sources ?? 0,
    total_catalogs: raw.catalogs ?? 0,
    total_schemas: raw.schemas ?? 0,
    total_tables: raw.tables ?? 0,
    total_columns: raw.columns ?? 0,
  };
}
