"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { ExpenseInput } from "@/lib/types"

interface ExpenseFormProps {
  onSubmit: (expense: ExpenseInput) => void
  onCancel: () => void
}

export default function ExpenseForm({ onSubmit, onCancel }: ExpenseFormProps) {
  const [expense, setExpense] = useState({
    vehicle: "",
    date: "",
    odo: "",
    expenseTask: "",
    totalCost: "",
    transactionType: "",
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setExpense({ ...expense, [name]: value })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      ...expense,
      odo: Number(expense.odo),
      totalCost: Number(expense.totalCost),
      transactionType: Number(expense.transactionType),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-xl font-semibold mb-4">Add New Expense</h2>

      <div>
        <Label htmlFor="vehicle">Vehicle</Label>
        <Select onValueChange={(value) => setExpense({ ...expense, vehicle: value })}>
          <SelectTrigger>
            <SelectValue placeholder="Select vehicle" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="XXX1">XXX1</SelectItem>
            <SelectItem value="XXX2">XXX2</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="date">Date</Label>
        <Input id="date" name="date" type="date" value={expense.date} onChange={handleChange} required />
      </div>

      <div>
        <Label htmlFor="odo">Odometer Reading</Label>
        <Input id="odo" name="odo" type="number" value={expense.odo} onChange={handleChange} required />
      </div>

      <div>
        <Label htmlFor="expenseTask">Expense Task</Label>
        <Input id="expenseTask" name="expenseTask" value={expense.expenseTask} onChange={handleChange} required />
      </div>

      <div>
        <Label htmlFor="totalCost">Total Cost (INR)</Label>
        <Input
          id="totalCost"
          name="totalCost"
          type="number"
          value={expense.totalCost}
          onChange={handleChange}
          required
        />
      </div>

      <div>
        <Label htmlFor="transactionType">Transaction Amount (INR)</Label>
        <Input
          id="transactionType"
          name="transactionType"
          type="number"
          value={expense.transactionType}
          onChange={handleChange}
          required
        />
      </div>

      <div className="flex justify-end space-x-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Add Expense</Button>
      </div>
    </form>
  )
}

