"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { CircleDollarSign, Clock, Package, Truck as TruckIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  api,
  type DashboardSummary,
  type RunDetail,
  type Solver,
  type TruckRoute,
  type Warehouse,
  type WeatherMode,
} from "@/lib/api";

const RouteMap = dynamic(() => import("./map/RouteMap"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full bg-gray-100 flex items-center justify-center rounded-md">
      <span className="text-gray-400">Loading map…</span>
    </div>
  ),
});

const POLL_INTERVAL_MS = 1500;

function KpiCard({
  title,
  value,
  hint,
  icon: Icon,
}: {
  title: string;
  value: string;
  hint: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  );
}

const SOLVER_LABELS: Record<string, string> = { heuristic: "Wave heuristic", dqn: "GNN + DQN" };
const TIME_SOURCE_LABELS: Record<string, string> = {
  offline: "offline time estimate",
  osrm: "OSRM road-network times",
  tomtom: "TomTom live traffic",
};
const WEATHER_LABELS: Record<string, string> = {
  live: "📡 Live",
  clear: "☀️ Clear",
  rain: "🌧️ Rain",
  storm: "⛈️ Storm",
};

export default function DashboardContent() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [routes, setRoutes] = useState<TruckRoute[]>([]);
  const [runs, setRuns] = useState<RunDetail[]>([]);
  const [solver, setSolver] = useState<Solver>("heuristic");
  const [weather, setWeather] = useState<WeatherMode>("live");
  const [onlineRouting, setOnlineRouting] = useState(false);
  const [runState, setRunState] = useState<"idle" | "running" | "failed">("idle");
  const [error, setError] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadDashboard = useCallback(async () => {
    try {
      const data = await api.getSummary();
      setSummary(data);
      if (data.latest_run?.status === "completed") {
        const { routes } = await api.getRunRoutes(data.latest_run.id);
        setRoutes(routes);
      }
      setRuns((await api.getRuns()).filter((run) => run.status === "completed"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach the backend API");
    }
  }, []);

  useEffect(() => {
    api.getWarehouses().then(setWarehouses).catch(() => undefined);
    loadDashboard();
    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, [loadDashboard]);

  const pollRun = useCallback(
    async (runId: number) => {
      let run: RunDetail;
      try {
        run = await api.getRun(runId);
      } catch (err) {
        setRunState("failed");
        setError(err instanceof Error ? err.message : "Lost contact with the run");
        return;
      }
      if (run.status === "completed") {
        setRunState("idle");
        await loadDashboard();
      } else if (run.status === "failed") {
        setRunState("failed");
        setError(run.error ?? "Optimization run failed");
      } else {
        pollTimer.current = setTimeout(() => pollRun(runId), POLL_INTERVAL_MS);
      }
    },
    [loadDashboard],
  );

  const loadSample = async () => {
    setSeeding(true);
    setError(null);
    try {
      await api.loadSample();
      await Promise.all([api.getWarehouses().then(setWarehouses), loadDashboard()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the sample dataset");
    } finally {
      setSeeding(false);
    }
  };

  const startOptimization = async () => {
    setRunState("running");
    setError(null);
    try {
      const run = await api.startOptimization({
        solver,
        weather_mode: weather,
        online_routing: onlineRouting,
      });
      pollRun(run.id);
    } catch (err) {
      setRunState("failed");
      setError(err instanceof Error ? err.message : "Could not start the optimization");
    }
  };

  const kpis = summary?.kpis;
  // A brand-new organization has no fleet or orders yet.
  const isEmpty =
    summary != null &&
    summary.warehouses === 0 &&
    summary.trucks === 0 &&
    summary.packages === 0;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <div className="flex items-center space-x-3">
          <label
            className="flex items-center gap-1.5 text-sm text-muted-foreground"
            title="Use real road-network travel times from the routing API (OSRM by default, or TomTom live traffic when a TomTom key is configured) instead of the offline estimator."
          >
            <input
              type="checkbox"
              checked={onlineRouting}
              onChange={(e) => setOnlineRouting(e.target.checked)}
              className="h-4 w-4"
            />
            Road-network times
          </label>
          <Select value={weather} onValueChange={(v) => setWeather(v as WeatherMode)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(WEATHER_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={solver} onValueChange={(v) => setSolver(v as Solver)}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(SOLVER_LABELS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={startOptimization}
            disabled={runState === "running" || isEmpty}
            title={isEmpty ? "Add warehouses, a vehicle, and orders first" : undefined}
          >
            {runState === "running"
              ? solver === "dqn"
                ? "Training DQN…"
                : "Optimizing…"
              : "Run optimization"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {isEmpty && (
        <Card>
          <CardContent className="py-8 text-center">
            <h2 className="text-lg font-semibold">Welcome to FleetUp 👋</h2>
            <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
              Your workspace is empty. Set up your fleet in three steps, then run an optimization to
              see traffic-aware routes on the map.
            </p>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
              <Button asChild>
                <Link href="/dashboard/warehouses">1. Add warehouses</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/dashboard/vehicles">2. Add vehicles</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href="/dashboard/orders">3. Add orders</Link>
              </Button>
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              Just exploring?{" "}
              <button
                onClick={loadSample}
                disabled={seeding}
                className="font-medium text-blue-600 hover:underline disabled:opacity-60"
              >
                {seeding ? "Loading…" : "Load a sample dataset"}
              </button>{" "}
              to try it instantly.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KpiCard
          title="Total cost"
          value={kpis ? kpis.total_cost.toLocaleString() : "—"}
          hint={
            kpis
              ? `drive ${Math.round(kpis.cost_breakdown.drive)} · fuel ${Math.round(kpis.cost_breakdown.fuel)} · late ${Math.round(kpis.cost_breakdown.lateness)}`
              : "Run an optimization"
          }
          icon={CircleDollarSign}
        />
        <KpiCard
          title="On-time rate"
          value={kpis?.on_time_rate != null ? `${(kpis.on_time_rate * 100).toFixed(1)}%` : "—"}
          hint={
            kpis
              ? `${kpis.on_time_deliveries}/${kpis.stops_served} delivered · ${kpis.failed_deliveries} failed`
              : "Run an optimization"
          }
          icon={Clock}
        />
        <KpiCard
          title="Distance & trips"
          value={kpis ? `${Math.round(kpis.total_distance_km)} km` : "—"}
          hint={
            kpis
              ? `${kpis.total_trips} trips · ${kpis.avg_stops_per_trip} stops/trip · ${Math.round(kpis.total_overtime_min)} min OT`
              : "Run an optimization"
          }
          icon={Package}
        />
        <KpiCard
          title="Fleet"
          value={summary ? String(summary.trucks) : "—"}
          hint={
            kpis
              ? `${kpis.active_trucks} active · ${(kpis.avg_peak_load_utilization * 100).toFixed(0)}% peak load`
              : "trucks registered"
          }
          icon={TruckIcon}
        />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle>Fleet routes</CardTitle>
          {summary?.latest_run && (
            <span className="text-xs text-muted-foreground">
              Run #{summary.latest_run.id} · {SOLVER_LABELS[summary.latest_run.solver]} ·{" "}
              {WEATHER_LABELS[summary.latest_run.weather] ?? summary.latest_run.weather}
              {summary.latest_run.weather_source.startsWith("live") && " (live)"} ·{" "}
              {TIME_SOURCE_LABELS[summary.latest_run.provider] ?? summary.latest_run.provider}
            </span>
          )}
        </CardHeader>
        <CardContent>
          <div className="h-[440px]">
            <RouteMap warehouses={warehouses} routes={routes} />
          </div>
        </CardContent>
      </Card>

      {runs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent runs — solver comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Run</th>
                    <th className="py-2 pr-4 font-medium">Solver</th>
                    <th className="py-2 pr-4 font-medium">Weather</th>
                    <th className="py-2 pr-4 font-medium">Total cost</th>
                    <th className="py-2 pr-4 font-medium">On-time</th>
                    <th className="py-2 pr-4 font-medium">Distance</th>
                    <th className="py-2 font-medium">Trips</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id} className="border-b last:border-0">
                      <td className="py-2 pr-4">#{run.id}</td>
                      <td className="py-2 pr-4">{SOLVER_LABELS[run.solver]}</td>
                      <td className="py-2 pr-4">{WEATHER_LABELS[run.weather]}</td>
                      <td className="py-2 pr-4 font-medium">
                        {run.kpis?.total_cost.toLocaleString() ?? "—"}
                      </td>
                      <td className="py-2 pr-4">
                        {run.kpis?.on_time_rate != null
                          ? `${(run.kpis.on_time_rate * 100).toFixed(1)}%`
                          : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        {run.kpis ? `${Math.round(run.kpis.total_distance_km)} km` : "—"}
                      </td>
                      <td className="py-2">{run.kpis?.total_trips ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
