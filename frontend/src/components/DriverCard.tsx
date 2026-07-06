import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Driver } from "@/lib/types"

export default function DriverCard({ driver }: { driver: Driver }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Driver ID: {driver.id}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <p>
            <strong>Assigned Vehicles:</strong> {driver.assignedVehicles || "None"}
          </p>
          <p>
            <strong>Hours Worked:</strong> {driver.hoursWorked || "NULL"}
          </p>
          <p>
            <strong>Status:</strong> {driver.status}
          </p>
          <p>
            <strong>Orders Delivered:</strong> {driver.ordersDelivered || "NULL"}
          </p>
          <p>
            <strong>Operational Zone:</strong> {driver.operationalZone}
          </p>
          <p>
            <strong>Employment Type:</strong> {driver.employmentType}
          </p>
          <p>
            <strong>License Number:</strong> {driver.licenseNumber}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

