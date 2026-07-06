"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, Plus } from "lucide-react"
import DriverForm from "./DriverForm"
import DriverCard from "./DriverCard"
import type { Driver } from "@/lib/types"

export default function DriverList() {
  const [showForm, setShowForm] = useState(false)
  const [drivers, setDrivers] = useState<Driver[]>([])

  const handleAddDriver = (driver: Driver) => {
    setDrivers([...drivers, driver])
    setShowForm(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Drivers</h1>
        <div className="flex items-center space-x-4">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <Input
              type="search"
              placeholder="Search drivers..."
              className="pl-8 pr-4 py-2 rounded-md border border-gray-300"
            />
          </div>
          <Button onClick={() => setShowForm(true)}>
            <Plus className="mr-2 h-4 w-4" /> Add New Driver
          </Button>
        </div>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded-lg w-full max-w-md">
            <DriverForm onSubmit={handleAddDriver} onCancel={() => setShowForm(false)} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {drivers.map((driver, index) => (
          <DriverCard key={index} driver={driver} />
        ))}
      </div>
    </div>
  )
}

