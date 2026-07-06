/** Typed client for the FleetUp backend API. */

// Use "localhost" (matching the frontend host) so the SameSite=Lax session
// cookie is sent on API calls; 127.0.0.1 would be treated as a different site.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

export interface Warehouse {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
}

export type WarehouseInput = Omit<Warehouse, "id">;

export interface Truck {
  id: number;
  name: string | null;
  capacity_kg: number;
  volume_m3: number;
  length_cm: number | null;
  width_cm: number | null;
  height_cm: number | null;
  warehouse_id: number;
}

export type TruckInput = Omit<Truck, "id">;

export interface Order {
  id: number;
  reference: string | null;
  recipient: string | null;
  address: string;
  latitude: number;
  longitude: number;
  weight_kg: number;
  volume_m3: number;
  length_cm: number | null;
  width_cm: number | null;
  height_cm: number | null;
  priority: number;
  window_start_min: number;
  window_end_min: number;
  warehouse_id: number | null;
}

export interface OrderInput {
  reference?: string | null;
  recipient?: string | null;
  address: string;
  latitude: number;
  longitude: number;
  weight_kg: number;
  volume_m3?: number | null;
  length_cm?: number | null;
  width_cm?: number | null;
  height_cm?: number | null;
  priority?: number;
  window_start_min?: number | null;
  window_end_min?: number | null;
  warehouse_id?: number | null;
}

export interface OrgSettings {
  id: number;
  name: string;
  working_hours_start_min: number;
  working_hours_end_min: number;
}

export interface GeocodeResult {
  found: boolean;
  latitude?: number;
  longitude?: number;
}

export interface ResolvedOrder extends OrderInput {
  latitude: number;
  longitude: number;
  volume_m3: number;
}

export interface ImportPreviewRow {
  row: number;
  status: "ok" | "error";
  errors: string[];
  note: string;
  order: ResolvedOrder;
}

export interface ImportPreview {
  rows: ImportPreviewRow[];
  summary: { total: number; ok: number; errors: number; geocoded: number };
}

export interface SampleLoadResult {
  warehouses: number;
  vehicles: number;
  orders: number;
}

export type Solver = "heuristic" | "dqn";
export type WeatherCondition = "clear" | "rain" | "storm";
export type WeatherMode = "live" | WeatherCondition;

export interface RunSummary {
  id: number;
  status: "queued" | "running" | "completed" | "failed";
  solver: Solver;
  weather: string; // resolved condition, or the requested mode until completed
  weather_source: string;
  online_routing: boolean;
  failure_rate: number;
  provider: string;
  geometry_provider: string;
  use_gnn: boolean;
  created_at: string;
  completed_at: string | null;
  error: string | null;
}

export interface CostBreakdown {
  drive: number;
  fuel: number;
  trips: number;
  waiting: number;
  lateness: number;
  overtime: number;
  unserved: number;
  total: number;
}

export interface FleetKpis {
  total_cost: number;
  cost_breakdown: CostBreakdown;
  total_packages: number;
  unassigned_packages: number;
  stops_served: number;
  failed_deliveries: number;
  on_time_deliveries: number;
  on_time_rate: number | null;
  total_drive_min: number;
  total_distance_km: number;
  total_waiting_min: number;
  total_overtime_min: number;
  total_trips: number;
  avg_stops_per_trip: number;
  active_trucks: number;
  idle_trucks: number;
  avg_peak_load_utilization: number;
}

export interface TruckStats {
  truck_id: number;
  warehouse_id: number;
  packages: number;
  trips: number;
  stops_served: number;
  failed: number;
  drive_min: number;
  distance_km: number;
  waiting_min: number;
  overtime_min: number;
  total_cost: number;
  peak_load_utilization: number;
}

export interface RunDetail extends RunSummary {
  kpis: FleetKpis | null;
  truck_stats: TruckStats[] | null;
}

export type VisitKind = "depart" | "delivery" | "failed" | "reload" | "break" | "return";

export interface Visit {
  truck_id: number;
  trip_number: number;
  kind: VisitKind;
  package_id: number | null;
  reference: string | null;
  recipient: string | null;
  latitude: number;
  longitude: number;
  eta_min: number;
  eta: string;
  departure: string;
  window: string | null;
  on_time: boolean | null;
}

export interface TruckRoute {
  truck_id: number;
  warehouse_id: number;
  color_index: number;
  visits: Visit[];
  // One road-following polyline (array of [lat, lon]) per trip, in order.
  geometry: [number, number][][];
}

export interface DashboardSummary {
  warehouses: number;
  trucks: number;
  packages: number;
  latest_run: RunSummary | null;
  kpis: FleetKpis | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include", // send the session cookie
    ...init,
  });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  getSummary: () => request<DashboardSummary>("/api/kpis"),

  getWarehouses: () => request<Warehouse[]>("/api/warehouses"),
  createWarehouse: (wh: WarehouseInput) =>
    request<Warehouse>("/api/warehouses", { method: "POST", body: JSON.stringify(wh) }),
  updateWarehouse: (id: number, wh: WarehouseInput) =>
    request<Warehouse>(`/api/warehouses/${id}`, { method: "PUT", body: JSON.stringify(wh) }),
  deleteWarehouse: (id: number) =>
    request<void>(`/api/warehouses/${id}`, { method: "DELETE" }),

  getTrucks: () => request<Truck[]>("/api/trucks"),
  createTruck: (truck: TruckInput) =>
    request<Truck>("/api/trucks", { method: "POST", body: JSON.stringify(truck) }),
  updateTruck: (id: number, truck: TruckInput) =>
    request<Truck>(`/api/trucks/${id}`, { method: "PUT", body: JSON.stringify(truck) }),
  deleteTruck: (id: number) => request<void>(`/api/trucks/${id}`, { method: "DELETE" }),

  getOrders: () => request<Order[]>("/api/orders"),
  createOrder: (order: OrderInput) =>
    request<Order>("/api/orders", { method: "POST", body: JSON.stringify(order) }),
  updateOrder: (id: number, order: OrderInput) =>
    request<Order>(`/api/orders/${id}`, { method: "PUT", body: JSON.stringify(order) }),
  deleteOrder: (id: number) => request<void>(`/api/orders/${id}`, { method: "DELETE" }),

  getOrgSettings: () => request<OrgSettings>("/api/org/settings"),
  updateOrgSettings: (settings: Omit<OrgSettings, "id">) =>
    request<OrgSettings>("/api/org/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),
  loadSample: () => request<SampleLoadResult>("/api/org/load-sample", { method: "POST" }),

  geocode: (address: string) =>
    request<GeocodeResult>("/api/geocode", {
      method: "POST",
      body: JSON.stringify({ address }),
    }),

  importPreview: async (file: File): Promise<ImportPreview> => {
    const form = new FormData();
    form.append("file", file);
    // No Content-Type header: the browser sets the multipart boundary itself.
    const res = await fetch(`${API_URL}/api/orders/import/preview`, {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`${res.status} ${res.statusText}: ${body}`);
    }
    return res.json();
  },
  importCommit: (orders: ResolvedOrder[]) =>
    request<{ added: number; updated: number; total: number }>("/api/orders/import/commit", {
      method: "POST",
      body: JSON.stringify({ orders }),
    }),
  importTemplateUrl: (format: "csv" | "xlsx") =>
    `${API_URL}/api/orders/import/template?format=${format}`,

  startOptimization: (options: {
    solver: Solver;
    weather_mode: WeatherMode;
    online_routing?: boolean;
    failure_rate?: number;
    use_gnn?: boolean;
    seed?: number;
  }) => request<RunSummary>("/api/optimize", { method: "POST", body: JSON.stringify(options) }),
  getRun: (id: number) => request<RunDetail>(`/api/runs/${id}`),
  getRuns: (limit = 8) => request<RunDetail[]>(`/api/runs?limit=${limit}`),
  getLatestRun: () => request<RunDetail>("/api/runs/latest"),
  getRunRoutes: (id: number) =>
    request<{ run_id: number; routes: TruckRoute[] }>(`/api/runs/${id}/routes`),
};
