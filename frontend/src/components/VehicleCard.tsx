"use client";

import { Box, Ruler, Trash2, Warehouse as WarehouseIcon, Weight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Truck } from "@/lib/api";

interface VehicleCardProps {
  truck: Truck;
  warehouseName?: string;
  onDelete: () => void;
}

export default function VehicleCard({ truck, warehouseName, onDelete }: VehicleCardProps) {
  const hasDims = truck.length_cm != null && truck.width_cm != null && truck.height_cm != null;
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>{truck.name?.trim() || `Vehicle #${truck.id}`}</CardTitle>
        <Button variant="ghost" size="icon" onClick={onDelete} aria-label={`Delete vehicle ${truck.id}`}>
          <Trash2 className="h-4 w-4 text-red-500" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p className="flex items-center gap-2">
          <Weight className="h-4 w-4 text-muted-foreground" />
          {truck.capacity_kg.toLocaleString()} kg payload
        </p>
        <p className="flex items-center gap-2">
          <Box className="h-4 w-4 text-muted-foreground" />
          {truck.volume_m3.toLocaleString()} m³ cargo volume
        </p>
        {hasDims && (
          <p className="flex items-center gap-2">
            <Ruler className="h-4 w-4 text-muted-foreground" />
            {truck.length_cm} × {truck.width_cm} × {truck.height_cm} cm bay
          </p>
        )}
        <p className="flex items-center gap-2">
          <WarehouseIcon className="h-4 w-4 text-muted-foreground" />
          {warehouseName ?? `Warehouse ${truck.warehouse_id}`}
        </p>
      </CardContent>
    </Card>
  );
}
