"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import VehicleCard from "./VehicleCard";
import VehicleForm from "./VehicleForm";
import { api, type Truck, type TruckInput, type Warehouse } from "@/lib/api";

export default function VehicleList() {
  const [trucks, setTrucks] = useState<Truck[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = () =>
    api
      .getTrucks()
      .then(setTrucks)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load trucks"));

  useEffect(() => {
    refresh();
    api.getWarehouses().then(setWarehouses).catch(() => undefined);
  }, []);

  const handleAdd = async (input: TruckInput) => {
    try {
      await api.createTruck(input);
      setShowForm(false);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add truck");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteTruck(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete truck");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Vehicles</h1>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="mr-2 h-4 w-4" /> Add Truck
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[1000]">
          <div className="bg-white p-6 rounded-lg w-full max-w-md">
            <VehicleForm warehouses={warehouses} onSubmit={handleAdd} onCancel={() => setShowForm(false)} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {trucks.map((truck) => (
          <VehicleCard
            key={truck.id}
            truck={truck}
            warehouseName={warehouses.find((wh) => wh.id === truck.warehouse_id)?.name}
            onDelete={() => handleDelete(truck.id)}
          />
        ))}
      </div>
    </div>
  );
}
