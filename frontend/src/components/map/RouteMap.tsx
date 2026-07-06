"use client";

import { useEffect, useMemo, useState } from "react";
import L from "leaflet";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { TruckRoute, Visit, Warehouse } from "@/lib/api";
import { ROUTE_COLORS } from "./colors";

interface RouteMapProps {
  warehouses: Warehouse[];
  routes: TruckRoute[];
}

const MUMBAI_CENTER: [number, number] = [19.076, 72.9];

function colorFor(route: TruckRoute): string {
  return ROUTE_COLORS[route.color_index % ROUTE_COLORS.length];
}

function isStop(v: Visit): boolean {
  return v.kind === "delivery" || v.kind === "failed";
}

/** A truck's trip polylines, preferring road geometry, else straight segments. */
function tripPaths(route: TruckRoute): [number, number][][] {
  if (route.geometry && route.geometry.length > 0) return route.geometry;
  return [route.visits.filter((v) => v.kind !== "break").map((v) => [v.latitude, v.longitude] as [number, number])];
}

/** Ordered delivery/failed stops with their 1-based visit number for a truck. */
function orderedStops(route: TruckRoute): { visit: Visit; order: number }[] {
  return route.visits.filter(isStop).map((visit, i) => ({ visit, order: i + 1 }));
}

function depotIcon(dimmed: boolean, start: boolean): L.DivIcon {
  const cls = `depot-badge${start ? " depot-badge--start" : ""}`;
  const flag = start ? `<span class="depot-flag">START</span>` : "";
  return L.divIcon({
    className: "",
    html: `<div class="depot-wrap" style="opacity:${dimmed ? 0.3 : 1}"><div class="${cls}">🏭</div>${flag}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

/** A small unlabelled dot for the overview (all-trucks) mode. */
function dotIcon(color: string, failed: boolean): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<div class="stop-dot" style="background:${failed ? "#9ca3af" : color}"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

/** A numbered badge for the focused truck's sequence. */
function badgeIcon(label: number, color: string, failed: boolean, selected: boolean): L.DivIcon {
  const bg = failed ? "#6b7280" : color;
  const size = selected ? 30 : 24;
  return L.divIcon({
    className: "",
    html: `<div class="stop-badge${selected ? " stop-badge--sel" : ""}" style="background:${bg}">${label}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

/** Fit the map to a set of points whenever they change (focus in / out). */
function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 1) map.fitBounds(points, { padding: [60, 60] });
  }, [map, points]);
  return null;
}

/** Fly to a stop when it's selected from the itinerary. */
function PanTo({ target }: { target: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo(target, Math.max(map.getZoom(), 13), { duration: 0.6 });
  }, [map, target]);
  return null;
}

function StopPopup({
  route,
  visit,
  order,
  total,
}: {
  route: TruckRoute;
  visit: Visit;
  order: number;
  total: number;
}) {
  const color = colorFor(route);
  const failed = visit.kind === "failed";
  const badge = failed
    ? { text: "Customer absent", bg: "#f3f4f6", fg: "#6b7280" }
    : visit.on_time
      ? { text: "On time", bg: "#dcfce7", fg: "#15803d" }
      : { text: "Late", bg: "#fee2e2", fg: "#b91c1c" };
  return (
    <div className="route-popup">
      <div className="route-popup__head">
        <span className="route-popup__dot" style={{ background: color }} />
        Truck {route.truck_id} · Trip {visit.trip_number}
      </div>
      <div className="route-popup__seq" style={{ color }}>
        Stop {order} <span>of {total}</span>
      </div>
      <div className="route-popup__row">
        <span>Order</span>
        <span>{visit.reference ?? `#${visit.package_id}`}</span>
      </div>
      {visit.recipient && (
        <div className="route-popup__row">
          <span>Recipient</span>
          <span>{visit.recipient}</span>
        </div>
      )}
      <div className="route-popup__row">
        <span>{failed ? "Attempted" : "ETA"}</span>
        <span>{visit.eta}</span>
      </div>
      <div className="route-popup__row">
        <span>Window</span>
        <span>{visit.window ?? "—"}</span>
      </div>
      <div style={{ marginTop: 6 }}>
        <span className="route-popup__badge" style={{ background: badge.bg, color: badge.fg }}>
          {badge.text}
        </span>
      </div>
    </div>
  );
}

export default function RouteMap({ warehouses, routes }: RouteMapProps) {
  const [focus, setFocus] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);

  // Clear any stop selection when switching trucks.
  useEffect(() => setSelected(null), [focus]);

  const activeRoutes = useMemo(
    () => routes.filter((r) => r.visits.some(isStop)),
    [routes],
  );

  const focusedRoute = useMemo(
    () => activeRoutes.find((r) => r.truck_id === focus) ?? null,
    [activeRoutes, focus],
  );

  // Fit to the focused truck when one is picked, else to the whole fleet.
  const bounds = useMemo<[number, number][]>(() => {
    const pts: [number, number][] = [];
    if (focusedRoute) {
      for (const path of tripPaths(focusedRoute)) for (const p of path) pts.push(p);
    } else {
      for (const w of warehouses) pts.push([w.latitude, w.longitude]);
      for (const r of activeRoutes)
        for (const path of tripPaths(r)) for (const p of path) pts.push(p);
    }
    return pts;
  }, [warehouses, activeRoutes, focusedRoute]);

  const depotTrucks = useMemo(() => {
    const map = new Map<number, number[]>();
    for (const r of activeRoutes) {
      const list = map.get(r.warehouse_id) ?? [];
      list.push(r.truck_id);
      map.set(r.warehouse_id, list);
    }
    return map;
  }, [activeRoutes]);

  // Trip-grouped itinerary for the focused truck (drives the left-hand panel).
  const itinerary = useMemo(() => {
    if (!focusedRoute) return null;
    const departOf = new Map<number, string>();
    for (const v of focusedRoute.visits)
      if (v.kind === "depart") departOf.set(v.trip_number, v.departure);
    const groups: { trip: number; departs: string; rows: { visit: Visit; order: number }[] }[] = [];
    for (const row of orderedStops(focusedRoute)) {
      let g = groups.find((x) => x.trip === row.visit.trip_number);
      if (!g) {
        g = { trip: row.visit.trip_number, departs: departOf.get(row.visit.trip_number) ?? "—", rows: [] };
        groups.push(g);
      }
      g.rows.push(row);
    }
    return groups;
  }, [focusedRoute]);

  const focusedStops = useMemo(
    () => (focusedRoute ? orderedStops(focusedRoute) : []),
    [focusedRoute],
  );
  const totalFocusStops = focusedStops.length;

  const panTarget = useMemo<[number, number] | null>(() => {
    if (selected == null) return null;
    const hit = focusedStops.find((s) => s.order === selected);
    return hit ? [hit.visit.latitude, hit.visit.longitude] : null;
  }, [selected, focusedStops]);

  const focusedWarehouse = focusedRoute
    ? warehouses.find((w) => w.id === focusedRoute.warehouse_id)
    : undefined;

  // A fresh organization has no warehouses and no routes yet.
  const hasData = warehouses.length > 0 || activeRoutes.length > 0;

  return (
    <div className="relative h-full w-full">
      <MapContainer center={MUMBAI_CENTER} zoom={11} className="h-full w-full rounded-md" scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={bounds} />
        <PanTo target={panTarget} />

        {warehouses.map((wh) => {
          const trucks = depotTrucks.get(wh.id) ?? [];
          const isStart = focusedRoute?.warehouse_id === wh.id;
          const dimmed = focus !== null && !isStart;
          return (
            <Marker
              key={`wh-${wh.id}`}
              position={[wh.latitude, wh.longitude]}
              icon={depotIcon(dimmed, isStart)}
              zIndexOffset={isStart ? 500 : 0}
            >
              <Popup>
                <div className="route-popup">
                  <div className="route-popup__head">🏭 {wh.name}</div>
                  <div className="route-popup__row">
                    <span>Warehouse</span>
                    <span>#{wh.id}</span>
                  </div>
                  <div className="route-popup__row">
                    <span>Trucks based here</span>
                    <span>{trucks.length ? trucks.join(", ") : "—"}</span>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {activeRoutes.map((route) => {
          const color = colorFor(route);
          const focused = focus === route.truck_id;
          const dimmed = focus !== null && !focused;
          const paths = tripPaths(route);

          return (
            <div key={`truck-${route.truck_id}`}>
              {paths.map((path, i) => (
                <Polyline
                  // Key includes focus state: Leaflet only applies `className`
                  // at path creation, so remount the line when focus toggles.
                  key={`path-${route.truck_id}-${i}-${focused}`}
                  positions={path}
                  eventHandlers={{ click: () => setFocus(route.truck_id) }}
                  pathOptions={{
                    color,
                    weight: focused ? 5 : 3,
                    opacity: dimmed ? 0.12 : focused ? 0.95 : 0.6,
                    className: focused ? "route-flow" : undefined,
                  }}
                />
              ))}

              {/* Overview: plain colored dots (no numbers) for every truck. */}
              {focus === null &&
                orderedStops(route).map(({ visit, order }) => (
                  <Marker
                    key={`dot-${route.truck_id}-${order}`}
                    position={[visit.latitude, visit.longitude]}
                    icon={dotIcon(color, visit.kind === "failed")}
                  >
                    <Popup>
                      <StopPopup route={route} visit={visit} order={order} total={orderedStops(route).length} />
                    </Popup>
                  </Marker>
                ))}

              {/* Focused truck: numbered sequence badges. */}
              {focused &&
                focusedStops.map(({ visit, order }) => (
                  <Marker
                    key={`badge-${route.truck_id}-${order}`}
                    position={[visit.latitude, visit.longitude]}
                    icon={badgeIcon(order, color, visit.kind === "failed", selected === order)}
                    zIndexOffset={1000 + (selected === order ? 500 : 0)}
                    eventHandlers={{ click: () => setSelected(order) }}
                  >
                    <Popup>
                      <StopPopup route={route} visit={visit} order={order} total={totalFocusStops} />
                    </Popup>
                  </Marker>
                ))}
            </div>
          );
        })}
      </MapContainer>

      {/* Left: itinerary for the focused truck — ties number ↔ package ↔ ETA. */}
      {focusedRoute && itinerary && (
        <div className="absolute left-3 top-3 z-[1000] flex max-h-[92%] w-56 flex-col overflow-hidden rounded-lg border border-gray-200 bg-white/95 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between gap-2 border-b px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full" style={{ background: colorFor(focusedRoute) }} />
              <span className="text-sm font-semibold">Truck {focusedRoute.truck_id}</span>
            </div>
            <button
              onClick={() => setFocus(null)}
              className="text-xs text-muted-foreground hover:text-gray-900"
            >
              ✕ Close
            </button>
          </div>
          <div className="border-b px-3 py-1.5 text-[11px] text-muted-foreground">
            {totalFocusStops} stops · {itinerary.length} trip{itinerary.length > 1 ? "s" : ""}
            {focusedWarehouse ? ` · from ${focusedWarehouse.name}` : ""}
          </div>
          <div className="overflow-y-auto">
            {itinerary.map((group) => (
              <div key={group.trip}>
                <div className="sticky top-0 bg-gray-50/95 px-3 py-1 text-[11px] font-medium text-gray-500 backdrop-blur">
                  Trip {group.trip} · departs {group.departs}
                </div>
                {group.rows.map(({ visit, order }) => {
                  const failed = visit.kind === "failed";
                  return (
                    <button
                      key={order}
                      onClick={() => setSelected(order)}
                      className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-gray-100 ${
                        selected === order ? "bg-gray-100" : ""
                      }`}
                    >
                      <span
                        className="flex h-5 w-5 flex-none items-center justify-center rounded-full text-[10px] font-bold text-white"
                        style={{ background: failed ? "#6b7280" : colorFor(focusedRoute) }}
                      >
                        {order}
                      </span>
                      <span className="flex-1 truncate">
                        <span className="font-medium">
                          {visit.reference ?? `Pkg #${visit.package_id}`}
                        </span>
                        <span className="text-muted-foreground"> · {visit.eta}</span>
                      </span>
                      <span
                        className={`h-2 w-2 flex-none rounded-full ${
                          failed ? "bg-gray-400" : visit.on_time ? "bg-green-500" : "bg-red-500"
                        }`}
                        title={failed ? "absent" : visit.on_time ? "on time" : "late"}
                      />
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Right: truck switcher (only when there are routes to switch between). */}
      {activeRoutes.length > 0 && (
      <div className="absolute right-3 top-3 z-[1000] max-h-[85%] w-44 overflow-y-auto rounded-lg border border-gray-200 bg-white/95 p-2 text-xs shadow-lg backdrop-blur">
        <button
          onClick={() => setFocus(null)}
          className={`mb-1 w-full rounded px-2 py-1 text-left font-medium ${
            focus === null ? "bg-gray-900 text-white" : "hover:bg-gray-100"
          }`}
        >
          All trucks
        </button>
        {activeRoutes.map((route) => {
          const deliveries = route.visits.filter((v) => v.kind === "delivery").length;
          return (
            <button
              key={`legend-${route.truck_id}`}
              onClick={() => setFocus(focus === route.truck_id ? null : route.truck_id)}
              className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left ${
                focus === route.truck_id ? "bg-gray-900 text-white" : "hover:bg-gray-100"
              }`}
            >
              <span
                className="inline-block h-3 w-3 flex-none rounded-full"
                style={{ background: colorFor(route) }}
              />
              <span className="flex-1">Truck {route.truck_id}</span>
              <span className={focus === route.truck_id ? "text-gray-300" : "text-muted-foreground"}>
                {deliveries}
              </span>
            </button>
          );
        })}
      </div>
      )}

      {/* Bottom hint changes with mode (hidden until there are routes). */}
      {activeRoutes.length > 0 && (
        <div className="absolute bottom-3 left-3 z-[1000] rounded-md bg-white/95 px-3 py-1.5 text-xs text-gray-600 shadow backdrop-blur">
          {focus === null
            ? "Tip: click a truck to trace its delivery order"
            : "Numbers = delivery order · animated flow = direction of travel"}
        </div>
      )}

      {/* Blank state: a brand-new workspace has nothing to plot yet. */}
      {!hasData && (
        <div className="pointer-events-none absolute inset-0 z-[1000] flex items-center justify-center">
          <div className="pointer-events-auto max-w-xs rounded-lg border border-gray-200 bg-white/95 px-5 py-4 text-center shadow-lg backdrop-blur">
            <div className="text-sm font-semibold text-gray-900">No routes to show yet</div>
            <p className="mt-1 text-xs text-gray-500">
              Add your warehouses, vehicles, and delivery orders, then run an optimization to see
              your fleet&apos;s routes on the map.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
