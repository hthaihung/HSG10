// ----------------------------------------------
// API Client - uses Vite env base URL
// Default fallback keeps local dev working
// ----------------------------------------------

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

function buildUrl(path) {
  return `${BASE_URL}${path}`;
}

async function fetchJSON(path) {
  const url = buildUrl(path);
  try {
    console.log(`[API] ➡️ ${url}`);
    const res = await fetch(url);
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      console.error(`[API] ❌ ${url} - ${res.status}`, text);
      throw new Error(`API ${res.status}: ${text || res.statusText}`);
    }
    const data = await res.json();
    console.log(`[API] ✅ ${url}`, data);
    return data;
  } catch (err) {
    console.error(`[API] NETWORK ERROR on ${url}:`, err);
    throw err;
  }
}

function qs(params) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v != null && v !== '' && String(v).toLowerCase() !== 'all') {
      p.set(k, v);
    }
  });
  const s = p.toString();
  return s ? `?${s}` : '';
}

export async function getFilters() {
  return fetchJSON('/api/filters');
}

export async function getStats(filters = {}) {
  return fetchJSON(`/api/stats${qs(filters)}`);
}

export async function getScoreDistribution(filters = {}) {
  return fetchJSON(`/api/score-distribution${qs(filters)}`);
}

export async function getTopSchools(filters = {}, metric = 'prizes') {
  return fetchJSON(`/api/top-schools${qs({ ...filters, metric })}`);
}

export async function getSubjectAverage(monThi) {
  if (!monThi || monThi.toLowerCase() === 'all' || monThi.toLowerCase() === 'tất cả') {
    return { mon_thi: monThi, average: 0.0 };
  }
  return fetchJSON(`/api/subject-average?mon_thi=${encodeURIComponent(monThi)}`);
}

export async function getInsights(filters = {}) {
  return fetchJSON(`/api/insights${qs(filters)}`);
}

export async function getTickerInsights(filters = {}) {
  return fetchJSON(`/api/ticker-insights${qs(filters)}`);
}

export async function compareSchools(school1, school2) {
  if (!school1 || !school2) throw new Error('Missing schools for comparison');
  return fetchJSON(`/api/advanced/compare-schools?school1=${encodeURIComponent(school1)}&school2=${encodeURIComponent(school2)}`);
}

export async function getStudents(filters = {}, search = '', page = 1, pageSize = 20) {
  return fetchJSON(`/api/students${qs({ ...filters, search, page, page_size: pageSize })}`);
}

export function getExportUrl(filters = {}, search = '') {
  return buildUrl(`/api/export${qs({ ...filters, search })}`);
}