"use client"

import { useEffect, type ReactNode } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  BarChart3,
  Car,
  Warehouse as WarehouseIcon,
  Package as PackageIcon,
  Users,
  DollarSign,
  Briefcase,
  UserCircle,
  Settings as SettingsIcon,
  LogOut,
  Loader2,
} from "lucide-react"
import { useAuth } from "@/components/auth/AuthProvider"

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: BarChart3 },
  { name: "Warehouses", href: "/dashboard/warehouses", icon: WarehouseIcon },
  { name: "Vehicles", href: "/dashboard/vehicles", icon: Car },
  { name: "Orders", href: "/dashboard/orders", icon: PackageIcon },
  { name: "Trips", href: "/dashboard/trips", icon: Briefcase },
  { name: "Drivers", href: "/dashboard/drivers", icon: Users },
  { name: "Expenses", href: "/dashboard/expenses", icon: DollarSign },
  { name: "Users", href: "/dashboard/users", icon: UserCircle },
  { name: "Settings", href: "/dashboard/settings", icon: SettingsIcon },
]

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { user, loading, logout } = useAuth()

  // Gate the app: unauthenticated visitors are sent to the login page.
  useEffect(() => {
    if (!loading && !user) router.replace("/login")
  }, [loading, user, router])

  if (loading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100 text-gray-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Loading…
      </div>
    )
  }

  const initials = user.full_name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()

  const handleLogout = async () => {
    await logout()
    router.replace("/login")
  }

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className="flex w-64 flex-col bg-blue-600 text-white">
        <div className="p-4">
          <Link href="/" className="text-2xl font-bold">
            FleetUp
          </Link>
          <p className="mt-0.5 truncate text-xs text-blue-200">{user.organization.name}</p>
        </div>

        <nav className="mt-6 flex-1">
          {navItems.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center px-4 py-3 text-sm font-medium transition-colors",
                pathname === item.href
                  ? "bg-blue-700 text-white"
                  : "text-blue-100 hover:bg-blue-700 hover:text-white",
              )}
            >
              <item.icon className="mr-3 h-5 w-5" />
              {item.name}
            </Link>
          ))}
        </nav>

        {/* Account footer. */}
        <div className="border-t border-blue-500/50 p-3">
          <div className="flex items-center gap-3 px-1 py-2">
            <span className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-blue-500 text-sm font-semibold">
              {initials || "U"}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user.full_name}</p>
              <p className="truncate text-xs text-blue-200">{user.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-1 flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-blue-100 transition-colors hover:bg-blue-700 hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-8">{children}</main>
    </div>
  )
}
