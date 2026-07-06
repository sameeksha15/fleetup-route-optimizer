"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, type RunDetail, type TruckRoute, type Visit } from "@/lib/api";
import { ROUTE_COLORS } from "@/components/map/colors";

const KIND_BADGES: Record<string, { label: string; className: string }> = {
  depart: { label: "Departs depot", className: "bg-blue-100 text-blue-700" },
  reload: { label: "Reload", className: "bg-indigo-100 text-indigo-700" },
  break: { label: "Lunch break", className: "bg-amber-100 text-amber-800" },
  return: { label: "Back at depot", className: "bg-gray-100 text-gray-600" },
  failed: { label: "Customer absent", className: "bg-red-100 text-red-700" },
};

function StatusBadge({ visit }: { visit: Visit }) {
  if (visit.kind === "delivery") {
    return (
      <span
        className={
          visit.on_time
            ? "rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700"
            : "rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700"
        }
      >
        {visit.on_time ? "On time" : "Late"}
      </span>
    );
  }
  const badge = KIND_BADGES[visit.kind];
  return <span className={`rounded-full px-2 py-0.5 text-xs ${badge.className}`}>{badge.label}</span>;
}

export default function TripsContent() {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [routes, setRoutes] = useState<TruckRoute[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const latest = await api.getLatestRun();
        setRun(latest);
        const { routes } = await api.getRunRoutes(latest.id);
        setRoutes(routes);
      } catch (err) {
        setError(
          err instanceof Error && err.message.startsWith("404")
            ? "No completed optimization runs yet — start one from the Dashboard."
            : "Failed to load trips from the backend API.",
        );
      }
    })();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Trips</h1>
        {run && (
          <span className="text-sm text-muted-foreground">
            Run #{run.id} · {run.solver} solver · {run.weather} weather
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {error}
        </div>
      )}

      {routes.map((route) => {
        const color = ROUTE_COLORS[route.color_index % ROUTE_COLORS.length];
        const rows = route.visits.filter((v) => v.kind !== "return");
        const hasWork = route.visits.some((v) => v.kind === "delivery" || v.kind === "failed");
        const stats = run?.truck_stats?.find((t) => t.truck_id === route.truck_id);
        return (
          <Card key={route.truck_id}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2 text-base">
                <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
                Truck {route.truck_id}
              </CardTitle>
              {stats && (
                <span className="text-xs text-muted-foreground">
                  {stats.trips} trips · {stats.stops_served} delivered
                  {stats.failed > 0 && ` · ${stats.failed} failed`} · {Math.round(stats.drive_min)} min /{" "}
                  {Math.round(stats.distance_km)} km · {(stats.peak_load_utilization * 100).toFixed(0)}%
                  peak load · cost {stats.total_cost.toLocaleString()}
                </span>
              )}
            </CardHeader>
            <CardContent>
              {!hasWork ? (
                <p className="text-sm text-muted-foreground">Idle — no packages assigned.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="py-2 pr-4 font-medium">Trip</th>
                        <th className="py-2 pr-4 font-medium">Event</th>
                        <th className="py-2 pr-4 font-medium">Arrival</th>
                        <th className="py-2 pr-4 font-medium">Departure</th>
                        <th className="py-2 pr-4 font-medium">Delivery window</th>
                        <th className="py-2 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((v, i) => (
                        <tr key={i} className="border-b last:border-0">
                          <td className="py-2 pr-4">#{v.trip_number}</td>
                          <td className="py-2 pr-4">
                            {v.package_id !== null ? `Package ${v.package_id}` : "—"}
                          </td>
                          <td className="py-2 pr-4">{v.eta}</td>
                          <td className="py-2 pr-4">{v.departure}</td>
                          <td className="py-2 pr-4">{v.window ?? "—"}</td>
                          <td className="py-2">
                            <StatusBadge visit={v} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
