"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { MapPin, Plus, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import ImportOrders from "./ImportOrders";
import { api, type Order, type OrderInput, type Warehouse } from "@/lib/api";

const LocationPicker = dynamic(() => import("./map/LocationPicker"), {
  ssr: false,
  loading: () => (
    <div className="flex h-64 w-full items-center justify-center rounded-md bg-gray-100 text-sm text-gray-400">
      Loading map…
    </div>
  ),
});

const PRIORITY_LABELS = ["Low", "Medium", "High"];
const AUTO = "__auto__";

function fmt(min: number) {
  const h = Math.floor(min / 60);
  const m = min % 60;
  const suffix = h < 12 ? "AM" : "PM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${suffix}`;
}
const toMinutes = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};

function AddOrder({
  warehouses,
  onCreated,
  onCancel,
}: {
  warehouses: Warehouse[];
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [reference, setReference] = useState("");
  const [recipient, setRecipient] = useState("");
  const [address, setAddress] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [weight, setWeight] = useState("");
  const [length, setLength] = useState("");
  const [width, setWidth] = useState("");
  const [height, setHeight] = useState("");
  const [volume, setVolume] = useState("");
  const [priority, setPriority] = useState("1");
  const [windowStart, setWindowStart] = useState("");
  const [windowEnd, setWindowEnd] = useState("");
  const [warehouseId, setWarehouseId] = useState(AUTO);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [geocoding, setGeocoding] = useState(false);
  const [geocodeMsg, setGeocodeMsg] = useState<string | null>(null);

  const coords =
    lat.trim() !== "" && lng.trim() !== "" ? { lat: Number(lat), lng: Number(lng) } : null;
  const numOrNull = (v: string) => (v.trim() === "" ? null : Number(v));

  const resolveAddress = async () => {
    if (!address.trim()) return;
    setGeocoding(true);
    setGeocodeMsg(null);
    try {
      const res = await api.geocode(address.trim());
      if (res.found && res.latitude != null && res.longitude != null) {
        setLat(String(res.latitude));
        setLng(String(res.longitude));
        setGeocodeMsg("Location found — adjust the pin if needed.");
      } else {
        setGeocodeMsg("Couldn't find that address. Drop a pin on the map instead.");
      }
    } catch {
      setGeocodeMsg("Geocoding failed. Drop a pin on the map instead.");
    } finally {
      setGeocoding(false);
    }
  };
  const hasDims = length && width && height;
  const canSubmit = address.trim() && coords && weight.trim() && (hasDims || volume.trim());

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || !coords) return;
    setSaving(true);
    setError(null);
    const payload: OrderInput = {
      reference: reference.trim() || null,
      recipient: recipient.trim() || null,
      address: address.trim(),
      latitude: coords.lat,
      longitude: coords.lng,
      weight_kg: Number(weight),
      length_cm: numOrNull(length),
      width_cm: numOrNull(width),
      height_cm: numOrNull(height),
      volume_m3: hasDims ? null : numOrNull(volume),
      priority: Number(priority),
      window_start_min: windowStart ? toMinutes(windowStart) : null,
      window_end_min: windowEnd ? toMinutes(windowEnd) : null,
      warehouse_id: warehouseId === AUTO ? null : Number(warehouseId),
    };
    try {
      await api.createOrder(payload);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add order");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/50 p-4">
      <form
        onSubmit={submit}
        className="max-h-[92vh] w-full max-w-lg space-y-4 overflow-y-auto rounded-lg bg-white p-6"
      >
        <h2 className="text-xl font-semibold">Add delivery order</h2>
        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="ref">Order reference</Label>
            <Input
              id="ref"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="e.g. INV-2043"
            />
          </div>
          <div>
            <Label htmlFor="rcpt">Recipient</Label>
            <Input
              id="rcpt"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              placeholder="e.g. Sharma Traders"
            />
          </div>
        </div>

        <div>
          <Label htmlFor="addr">Delivery address</Label>
          <div className="flex gap-2">
            <Input
              id="addr"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Street, area, city"
              required
            />
            <Button
              type="button"
              variant="outline"
              onClick={resolveAddress}
              disabled={geocoding || !address.trim()}
              className="whitespace-nowrap"
            >
              <MapPin className="mr-1 h-4 w-4" />
              {geocoding ? "Locating…" : "Locate"}
            </Button>
          </div>
          {geocodeMsg && <p className="mt-1 text-xs text-muted-foreground">{geocodeMsg}</p>}
        </div>

        <div>
          <Label>Location — click the map to drop a pin</Label>
          <LocationPicker
            value={coords}
            onChange={(la, ln) => {
              setLat(String(la));
              setLng(String(ln));
            }}
          />
          <div className="mt-2 grid grid-cols-2 gap-3">
            <Input
              aria-label="Latitude"
              type="number"
              step="any"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              placeholder="Latitude"
              required
            />
            <Input
              aria-label="Longitude"
              type="number"
              step="any"
              value={lng}
              onChange={(e) => setLng(e.target.value)}
              placeholder="Longitude"
              required
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="wt">Weight (kg)</Label>
            <Input
              id="wt"
              type="number"
              min="0.1"
              step="0.1"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              required
            />
          </div>
          <div>
            <Label>Priority</Label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRIORITY_LABELS.map((label, i) => (
                  <SelectItem key={i} value={String(i)}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div>
          <Label>Parcel dimensions (cm)</Label>
          <p className="mb-1 text-xs text-muted-foreground">
            Volume is derived from these. Leave blank and enter a volume below instead.
          </p>
          <div className="grid grid-cols-3 gap-3">
            <Input
              aria-label="Length (cm)"
              type="number"
              min="1"
              value={length}
              onChange={(e) => setLength(e.target.value)}
              placeholder="Length"
            />
            <Input
              aria-label="Width (cm)"
              type="number"
              min="1"
              value={width}
              onChange={(e) => setWidth(e.target.value)}
              placeholder="Width"
            />
            <Input
              aria-label="Height (cm)"
              type="number"
              min="1"
              value={height}
              onChange={(e) => setHeight(e.target.value)}
              placeholder="Height"
            />
          </div>
        </div>

        {!hasDims && (
          <div>
            <Label htmlFor="vol">Volume (m³)</Label>
            <Input
              id="vol"
              type="number"
              min="0.001"
              step="0.001"
              value={volume}
              onChange={(e) => setVolume(e.target.value)}
              placeholder="Required if no dimensions"
            />
          </div>
        )}

        <div>
          <Label>Delivery window (optional — defaults to working hours)</Label>
          <div className="grid grid-cols-2 gap-3">
            <Input
              aria-label="Window start"
              type="time"
              value={windowStart}
              onChange={(e) => setWindowStart(e.target.value)}
            />
            <Input
              aria-label="Window end"
              type="time"
              value={windowEnd}
              onChange={(e) => setWindowEnd(e.target.value)}
            />
          </div>
        </div>

        <div>
          <Label>Source warehouse</Label>
          <Select value={warehouseId} onValueChange={setWarehouseId}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={AUTO}>Auto — nearest warehouse</SelectItem>
              {warehouses.map((wh) => (
                <SelectItem key={wh.id} value={String(wh.id)}>
                  {wh.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex justify-end gap-3 pt-1">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving || !canSubmit}>
            {saving ? "Saving…" : "Add order"}
          </Button>
        </div>
      </form>
    </div>
  );
}

export default function OrderList() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const warehouseName = useMemo(() => {
    const map = new Map(warehouses.map((w) => [w.id, w.name]));
    return (id: number | null) => (id == null ? "Auto" : map.get(id) ?? `#${id}`);
  }, [warehouses]);

  const refresh = () =>
    api
      .getOrders()
      .then(setOrders)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load orders"));

  useEffect(() => {
    refresh();
    api.getWarehouses().then(setWarehouses).catch(() => undefined);
  }, []);

  const handleDelete = async (id: number) => {
    setError(null);
    try {
      await api.deleteOrder(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete order");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Orders</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowImport(true)}>
            <Upload className="mr-2 h-4 w-4" /> Import CSV / Excel
          </Button>
          <Button onClick={() => setShowForm(true)}>
            <Plus className="mr-2 h-4 w-4" /> Add order
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {orders.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No orders yet. Add deliveries one at a time here, or bulk-import a CSV/Excel file (coming
            soon).
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="px-4 py-2 font-medium">Reference</th>
                  <th className="px-4 py-2 font-medium">Recipient</th>
                  <th className="px-4 py-2 font-medium">Address</th>
                  <th className="px-4 py-2 font-medium">Weight</th>
                  <th className="px-4 py-2 font-medium">Priority</th>
                  <th className="px-4 py-2 font-medium">Window</th>
                  <th className="px-4 py-2 font-medium">Warehouse</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.id} className="border-b last:border-0">
                    <td className="px-4 py-2 font-medium">{o.reference ?? `#${o.id}`}</td>
                    <td className="px-4 py-2">{o.recipient ?? "—"}</td>
                    <td className="max-w-[220px] truncate px-4 py-2" title={o.address}>
                      {o.address}
                    </td>
                    <td className="px-4 py-2">{o.weight_kg} kg</td>
                    <td className="px-4 py-2">{PRIORITY_LABELS[o.priority] ?? o.priority}</td>
                    <td className="px-4 py-2 whitespace-nowrap">
                      {fmt(o.window_start_min)} – {fmt(o.window_end_min)}
                    </td>
                    <td className="px-4 py-2">{warehouseName(o.warehouse_id)}</td>
                    <td className="px-4 py-2 text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(o.id)}
                        aria-label={`Delete order ${o.reference ?? o.id}`}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {showForm && (
        <AddOrder
          warehouses={warehouses}
          onCreated={() => {
            setShowForm(false);
            refresh();
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {showImport && (
        <ImportOrders
          onDone={() => {
            setShowImport(false);
            refresh();
          }}
          onCancel={() => setShowImport(false)}
        />
      )}
    </div>
  );
}
