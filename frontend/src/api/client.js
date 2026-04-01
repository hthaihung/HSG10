const BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

function qs(params) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value != null && value !== "" && String(value).toLowerCase() !== "all") {
      searchParams.set(key, value);
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

async function apiFetch(endpoint, options = {}) {
  const res = await fetch(`${BASE_URL}${endpoint}`, options);

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }

  return res.json();
}

export async function getFilters() {
  return apiFetch("/api/filters");
}

export async function getStats(filters = {}) {
  return apiFetch(`/api/stats${qs(filters)}`);
}

export async function getScoreDistribution(filters = {}) {
  return apiFetch(`/api/score-distribution${qs(filters)}`);
}

export async function getTopSchools(filters = {}, metric = "prizes") {
  return apiFetch(`/api/top-schools${qs({ ...filters, metric })}`);
}

export async function getSubjectAverage(monThi) {
  if (!monThi || monThi.toLowerCase() === "all" || monThi.toLowerCase() === "tat ca") {
    return { mon_thi: monThi, average: 0.0 };
  }

  return apiFetch(`/api/subject-average?mon_thi=${encodeURIComponent(monThi)}`);
}

export async function getTickerInsights(filters = {}) {
  return apiFetch(`/api/ticker-insights${qs(filters)}`);
}

export async function getStudents(filters = {}, search = "", page = 1, pageSize = 20) {
  return apiFetch(`/api/students${qs({ ...filters, search, page, page_size: pageSize })}`);
}
