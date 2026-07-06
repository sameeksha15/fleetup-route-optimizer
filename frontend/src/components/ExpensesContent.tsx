"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card } from "@/components/ui/card"
import { FileDown, Pencil, Trash2, Search, Book } from "lucide-react"
import ExpenseForm from "./ExpenseForm"
import type { Expense, ExpenseInput } from "@/lib/types"

const initialExpenses: Expense[] = [
  {
    id: "1",
    vehicle: "XXX1",
    date: "10/21/22",
    odo: 24561,
    expenseTask: "Air Filter",
    totalCost: 642.0,
    transactionType: 320.0,
  },
  {
    id: "2",
    vehicle: "XXX2",
    date: "10/03/22",
    odo: 24561,
    expenseTask: "Oil Change",
    totalCost: 542.0,
    transactionType: 210.0,
  },
]

export default function ExpensesContent() {
  const [expenses, setExpenses] = useState<Expense[]>(initialExpenses)
  const [showForm, setShowForm] = useState(false)
  const totalCost = expenses.reduce((sum, expense) => sum + expense.totalCost, 0)

  const handleDelete = (id: string) => {
    setExpenses(expenses.filter((expense) => expense.id !== id))
  }

  const handleAddExpense = (expense: ExpenseInput) => {
    setExpenses([...expenses, { ...expense, id: Math.random().toString() }])
    setShowForm(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Other expenses</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon">
            <Book className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon">
            <FileDown className="h-4 w-4" />
            <span className="sr-only">Download PDF</span>
          </Button>
          <Button onClick={() => setShowForm(true)}>Add Expenses</Button>
        </div>
      </div>

      <Card className="p-6">
        <div className="text-2xl font-bold text-green-600 mb-4">{totalCost.toFixed(2)} INR</div>
        <div className="text-sm text-gray-500">Total Cost</div>
      </Card>

      <div className="flex gap-4 mb-6">
        <Select>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Group" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="group1">Group 1</SelectItem>
            <SelectItem value="group2">Group 2</SelectItem>
          </SelectContent>
        </Select>

        <Select>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Vehicle name" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="xxx1">XXX1</SelectItem>
            <SelectItem value="xxx2">XXX2</SelectItem>
          </SelectContent>
        </Select>

        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
          <Input className="pl-8" placeholder="Search fleet-up" />
        </div>

        <Select>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="09/10/22 to 09/11/22" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="current">09/10/22 to 09/11/22</SelectItem>
            <SelectItem value="previous">09/09/22 to 09/10/22</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="text-left py-3 px-4">Vehicle</th>
              <th className="text-left py-3 px-4">Date</th>
              <th className="text-left py-3 px-4">Odo</th>
              <th className="text-left py-3 px-4">Expense Task</th>
              <th className="text-left py-3 px-4">Total Cost</th>
              <th className="text-left py-3 px-4">Transaction Type</th>
              <th className="text-left py-3 px-4">Edit/Delete</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((expense) => (
              <tr key={expense.id} className="border-b">
                <td className="py-3 px-4">{expense.vehicle}</td>
                <td className="py-3 px-4">{expense.date}</td>
                <td className="py-3 px-4">{expense.odo}</td>
                <td className="py-3 px-4">{expense.expenseTask}</td>
                <td className="py-3 px-4">{expense.totalCost.toFixed(2)} INR</td>
                <td className="py-3 px-4">{expense.transactionType.toFixed(2)} INR</td>
                <td className="py-3 px-4">
                  <div className="flex gap-2">
                    <Button variant="ghost" size="icon">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(expense.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded-lg w-full max-w-md">
            <ExpenseForm onSubmit={handleAddExpense} onCancel={() => setShowForm(false)} />
          </div>
        </div>
      )}
    </div>
  )
}

