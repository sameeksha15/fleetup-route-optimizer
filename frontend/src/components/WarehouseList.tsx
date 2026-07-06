"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { MapPin, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type Warehouse } from "@/lib/api";

const LocationPicker = dynamic(() => import("./map/LocationPicker"), {
  ssr: false,
  loading: () => (
    <div className="flex h-64 w-full items-center justify-center rounded-md bg-gray-100 text-sm text-gray-400">
      Loading map…
    </div>
  ),
});

function AddWarehouse({
  onCreated,
  onCancel,
}: {
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const coords =
    lat.trim() !== "" && lng.trim() !== "" ? { lat: Number(lat), lng: Number(lng) } : null;

  const setFromMap = (la: number, ln: number) => {
    setLat(String(la));
    setLng(String(ln));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !coords) return;
    setSaving(true);
    setError(null);
    try {
      await api.createWarehouse({ name: name.trim(), latitude: coords.lat, longitude: coords.lng });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add warehouse");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/50 p-4">
      <form onSubmit={submit} className="w-full max-w-lg space-y-4 rounded-lg bg-white p-6">
        <h2 className="text-xl font-semibold">Add warehouse</h2>
        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}
        <div>
          <Label htmlFor="wh-name">Name</Label>
          <Input
            id="wh-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Bhiwandi Hub"
            required
          />
        </div>
        <div>
          <Label>Location — click the map to drop a pin</Label>
          <LocationPicker value={coords} onChange={setFromMap} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="wh-lat">Latitude</Label>
            <Input
              id="wh-lat"
              type="number"
              step="any"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="wh-lng">Longitude</Label>
            <Input
              id="wh-lng"
              type="number"
              step="any"
              value={lng}
              onChange={(e) => setLng(e.target.value)}
              required
            />
          </div>
        </div>
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving || !name.trim() || !coords}>
            {saving ? "Saving…" : "Add warehouse"}
          </Button>
        </div>
      </form>
    </div>
  );
}

export default function WarehouseList() {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = () =>
    api
      .getWarehouses()
      .then(setWarehouses)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load warehouses"));

  useEffect(() => {
    refresh();
  }, []);

  const handleDelete = async (id: number) => {
    setError(null);
    try {
      await api.deleteWarehouse(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete warehouse");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Warehouses</h1>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="mr-2 h-4 w-4" /> Add warehouse
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {warehouses.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No warehouses yet. Add the depots your fleet dispatches from — click the map to place
            each one precisely.
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {warehouses.map((wh) => (
          <Card key={wh.id}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">{wh.name}</CardTitle>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleDelete(wh.id)}
                aria-label={`Delete ${wh.name}`}
              >
                <Trash2 className="h-4 w-4 text-red-500" />
              </Button>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              <p className="flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                {wh.latitude.toFixed(4)}, {wh.longitude.toFixed(4)}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {showForm && (
        <AddWarehouse
          onCreated={() => {
            setShowForm(false);
            refresh();
          }}
          onCancel={() => setShowForm(false)}
        />
      )}
    </div>
  );
}
