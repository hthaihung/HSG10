const API_TIMEOUT_MS = 5000;

const API_BASE_URL_1 = (import.meta.env.VITE_API_URL_1 || import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE_URL_2 = (import.meta.env.VITE_API_URL_2 || "").replace(/\/+$/, "");

function buildUrl(baseUrl, path) {
  return `${baseUrl}${path}`;
}

function qs(params) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value != null && value !== "" && String(value).toLowerCase() !== "all") {
      p.set(key, value);
    }
  });
  const s = p.toString();
  return s ? `?${s}` : "";
}

async function fetchFromBase(baseUrl, endpoint, options = {}) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  const url = buildUrl(baseUrl, endpoint);

  try {
    console.log(`[API] -> ${url}`);
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`API ${response.status}: ${text || response.statusText}`);
    }

    return response;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function fetchWithFallback(endpoint, options = {}) {
  const bases = [API_BASE_URL_1, API_BASE_URL_2].filter(Boolean);
  let lastError;

  for (const baseUrl of bases) {
    try {
      return await fetchFromBase(baseUrl, endpoint, options);
    } catch (error) {
      lastError = error;
      console.error(`[API] failed on ${baseUrl}${endpoint}`, error);
    }
  }

  throw lastError || new Error("No API base URL configured");
}

async function fetchJSON(endpoint, options = {}) {
  const response = await fetchWithFallback(endpoint, options);
  return response.json();
}

export async function getFilters() {
  return fetchJSON("/api/filters");
}

export async function getStats(filters = {}) {
  return fetchJSON(`/api/stats${qs(filters)}`);
}

export async function getScoreDistribution(filters = {}) {
  return fetchJSON(`/api/score-distribution${qs(filters)}`);
}

export async function getTopSchools(filters = {}, metric = "prizes") {
  return fetchJSON(`/api/top-schools${qs({ ...filters, metric })}`);
}

export async function getSubjectAverage(monThi) {
  if (!monThi || monThi.toLowerCase() === "all" || monThi.toLowerCase() === "tat ca") {
    return { mon_thi: monThi, average: 0.0 };
  }
  return fetchJSON(`/api/subject-average?mon_thi=${encodeURIComponent(monThi)}`);
}

// Backend does not expose /api/insights yet.
// export async function getInsights(filters = {}) {
//   return fetchJSON(`/api/insights${qs(filters)}`);
// }

export async function getTickerInsights(filters = {}) {
  return fetchJSON(`/api/ticker-insights${qs(filters)}`);
}

// Backend does not expose /api/advanced/compare-schools yet.
// export async function compareSchools(school1, school2) {
//   if (!school1 || !school2) throw new Error("Missing schools for comparison");
//   return fetchJSON(`/api/advanced/compare-schools?school1=${encodeURIComponent(school1)}&school2=${encodeURIComponent(school2)}`);
// }

export async function getStudents(filters = {}, search = "", page = 1, pageSize = 20) {
  return fetchJSON(`/api/students${qs({ ...filters, search, page, page_size: pageSize })}`);
}
