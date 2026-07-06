import Link from "next/link";
import type { ReactNode } from "react";
import { Truck } from "lucide-react";
import RouteAnimation from "@/components/landing/RouteAnimation";

/** Split-screen shell for the login / signup pages: brand panel + form. */
export default function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      {/* Brand panel (hidden on small screens). */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-slate-950 p-10 text-white lg:flex">
        <div className="pointer-events-none absolute -left-24 top-16 h-80 w-80 rounded-full bg-blue-600/20 blur-3xl" />
        <div className="pointer-events-none absolute -right-16 bottom-10 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />

        <Link href="/" className="relative flex items-center gap-2 font-semibold">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
            <Truck className="h-4 w-4" strokeWidth={2.2} />
          </span>
          <span className="text-lg">FleetUp</span>
        </Link>

        <div className="relative mx-auto w-full max-w-sm">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3 shadow-2xl">
            <div className="aspect-[4/3] w-full overflow-hidden rounded-xl bg-slate-900/60">
              <RouteAnimation />
            </div>
          </div>
        </div>

        <p className="relative max-w-sm text-sm leading-relaxed text-slate-400">
          Traffic-aware route optimization for delivery fleets across Mumbai, Navi Mumbai, and Thane.
        </p>
      </div>

      {/* Form panel. */}
      <div className="flex w-full items-center justify-center px-5 py-12 lg:w-1/2">
        <div className="w-full max-w-sm">
          <Link href="/" className="mb-8 flex items-center gap-2 font-semibold lg:hidden">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
              <Truck className="h-4 w-4" strokeWidth={2.2} />
            </span>
            <span className="text-lg text-slate-900">FleetUp</span>
          </Link>

          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
          <p className="mt-1.5 text-sm text-slate-500">{subtitle}</p>

          <div className="mt-8">{children}</div>

          <div className="mt-6 text-center text-sm text-slate-500">{footer}</div>
        </div>
      </div>
    </div>
  );
}
