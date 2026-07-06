"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { Driver } from "@/lib/types"

interface DriverFormProps {
  onSubmit: (driver: Driver) => void
  onCancel: () => void
}

export default function DriverForm({ onSubmit, onCancel }: DriverFormProps) {
  const [driver, setDriver] = useState<Driver>({
    id: "",
    assignedVehicles: "",
    hoursWorked: null,
    status: "IDLE",
    ordersDelivered: null,
    operationalZone: "",
    employmentType: "",
    licenseNumber: "",
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setDriver({ ...driver, [name]: value })
  }

  const handleSelectChange = (name: keyof Driver, value: string) => {
    setDriver({ ...driver, [name]: value })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(driver)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-xl font-semibold mb-4">Add New Driver</h2>
      <div>
        <Label htmlFor="id">Driver ID</Label>
        <Input id="id" name="id" value={driver.id} onChange={handleChange} required />
      </div>
      <div>
        <Label htmlFor="assignedVehicles">Assigned Vehicles</Label>
        <Input
          id="assignedVehicles"
          name="assignedVehicles"
          value={driver.assignedVehicles}
          onChange={handleChange}
          placeholder="Enter vehicle IDs separated by commas"
        />
      </div>
      <div>
        <Label htmlFor="hoursWorked">Number of Hours Worked</Label>
        <Input
          id="hoursWorked"
          name="hoursWorked"
          type="number"
          value={driver.hoursWorked || ""}
          onChange={handleChange}
          placeholder="NULL"
        />
      </div>
      <div>
        <Label htmlFor="status">Current Status</Label>
        <Select name="status" onValueChange={(value) => handleSelectChange("status", value)} required>
          <SelectTrigger>
            <SelectValue placeholder="Select status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="IDLE">IDLE</SelectItem>
            <SelectItem value="Driving">Driving</SelectItem>
            <SelectItem value="Not Driving">Not Driving</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label htmlFor="ordersDelivered">Number of Orders Delivered</Label>
        <Input
          id="ordersDelivered"
          name="ordersDelivered"
          type="number"
          value={driver.ordersDelivered || ""}
          onChange={handleChange}
          placeholder="NULL"
        />
      </div>
      <div>
        <Label htmlFor="operationalZone">Operational Zone</Label>
        <Input
          id="operationalZone"
          name="operationalZone"
          value={driver.operationalZone}
          onChange={handleChange}
          required
        />
      </div>
      <div>
        <Label htmlFor="employmentType">Employment Type</Label>
        <Select name="employmentType" onValueChange={(value) => handleSelectChange("employmentType", value)} required>
          <SelectTrigger>
            <SelectValue placeholder="Select employment type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="Contract">Contract Based</SelectItem>
            <SelectItem value="FullTime">Full Time</SelectItem>
            <SelectItem value="DailyWage">Daily Wage</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label htmlFor="licenseNumber">License Number</Label>
        <Input id="licenseNumber" name="licenseNumber" value={driver.licenseNumber} onChange={handleChange} required />
      </div>
      <div className="flex justify-end space-x-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Add Driver</Button>
      </div>
    </form>
  )
}

