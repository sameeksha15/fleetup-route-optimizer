/** Shared types for locally managed (non-API) dashboard data. */

export interface Driver {
  id: string;
  assignedVehicles: string;
  hoursWorked: number | null;
  status: string;
  ordersDelivered: number | null;
  operationalZone: string;
  employmentType: string;
  licenseNumber: string;
}

export interface Expense {
  id: string;
  vehicle: string;
  date: string;
  odo: number;
  expenseTask: string;
  totalCost: number;
  transactionType: number;
}

export type ExpenseInput = Omit<Expense, "id">;
