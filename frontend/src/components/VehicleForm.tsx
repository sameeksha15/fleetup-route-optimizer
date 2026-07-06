"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { TruckInput, Warehouse } from "@/lib/api";

interface VehicleFormProps {
  warehouses: Warehouse[];
  onSubmit: (truck: TruckInput) => void;
  onCancel: () => void;
}

export default function VehicleForm({ warehouses, onSubmit, onCancel }: VehicleFormProps) {
  const [name, setName] = useState("");
  const [capacity, setCapacity] = useState("1000");
  const [volume, setVolume] = useState("9");
  const [length, setLength] = useState("");
  const [width, setWidth] = useState("");
  const [height, setHeight] = useState("");
  const [warehouseId, setWarehouseId] = useState<string>("");

  const numOrNull = (v: string) => (v.trim() === "" ? null : Number(v));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!warehouseId) return;
    onSubmit({
      name: name.trim() || null,
      capacity_kg: Number(capacity),
      volume_m3: Number(volume),
      length_cm: numOrNull(length),
      width_cm: numOrNull(width),
      height_cm: numOrNull(height),
      warehouse_id: Number(warehouseId),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-xl font-semibold mb-4">Add vehicle</h2>
      <div>
        <Label htmlFor="name">Name / plate (optional)</Label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Tempo MH-01-AB-1234"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="capacity">Payload capacity (kg)</Label>
          <Input
            id="capacity"
            type="number"
            min="1"
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="volume">Cargo volume (m³)</Label>
          <Input
            id="volume"
            type="number"
            min="0.1"
            step="0.1"
            value={volume}
            onChange={(e) => setVolume(e.target.value)}
            required
          />
        </div>
      </div>
      <div>
        <Label>Cargo-bay dimensions (cm, optional)</Label>
        <p className="mb-1 text-xs text-muted-foreground">
          Used to reject parcels too large to physically fit.
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
      <div>
        <Label>Home warehouse</Label>
        <Select value={warehouseId} onValueChange={setWarehouseId} required>
          <SelectTrigger>
            <SelectValue placeholder="Select warehouse" />
          </SelectTrigger>
          <SelectContent>
            {warehouses.map((wh) => (
              <SelectItem key={wh.id} value={String(wh.id)}>
                {wh.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex justify-end space-x-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={!warehouseId}>
          Add vehicle
        </Button>
      </div>
    </form>
  );
}
