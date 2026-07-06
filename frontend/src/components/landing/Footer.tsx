"use client";

import { useRef } from "react";
import Link from "next/link";
import { Truck, ArrowRight } from "lucide-react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Button } from "@/components/ui/button";

const columns: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "Product",
    links: [
      { label: "How it works", href: "#how" },
      { label: "Open dashboard", href: "/dashboard" },
      { label: "Log in", href: "/login" },
      { label: "Sign up", href: "/signup" },
    ],
  },
  {
    title: "Platform",
    links: [
      { label: "Live traffic routing", href: "#how" },
      { label: "Time windows", href: "#how" },
      { label: "Driver shifts", href: "#how" },
      { label: "Parcel fit", href: "#how" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "#" },
      { label: "Privacy", href: "#" },
      { label: "Terms", href: "#" },
    ],
  },
];

export default function Footer() {
  const root = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      gsap.registerPlugin(ScrollTrigger);
      const mm = gsap.matchMedia();

      mm.add("(prefers-reduced-motion: no-preference)", () => {
        // The closing CTA lifts in.
        gsap.from("[data-cta-band]", {
          y: 40,
          opacity: 0,
          duration: 1,
          ease: "expo.out",
          scrollTrigger: { trigger: "[data-cta-band]", start: "top 85%", once: true },
        });
        // The faint route inside it traces once it's in view.
        gsap.fromTo(
          "[data-cta-route]",
          { strokeDashoffset: 1 },
          {
            strokeDashoffset: 0,
            duration: 2,
            ease: "power2.inOut",
            scrollTrigger: { trigger: "[data-cta-band]", start: "top 80%", once: true },
          },
        );
        // Footer columns stagger up.
        gsap.from("[data-fcol]", {
          y: 22,
          opacity: 0,
          duration: 0.7,
          stagger: 0.1,
          ease: "expo.out",
          scrollTrigger: { trigger: "[data-foot]", start: "top 88%", once: true },
        });
      });
    },
    { scope: root },
  );

  return (
    <footer ref={root} className="relative overflow-hidden bg-white">
      {/* Closing CTA: a committed gradient band, the page's contrast moment. */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <div
          data-cta-band
          className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 px-8 py-20 text-center shadow-[0_30px_80px_-40px_rgba(37,99,235,0.7)]"
        >
          {/* Faint route texture, on-theme, tracing in. */}
          <svg
            className="pointer-events-none absolute inset-0 h-full w-full opacity-30"
            viewBox="0 0 1200 400"
            fill="none"
            preserveAspectRatio="xMidYMid slice"
            aria-hidden="true"
          >
            <path
              data-cta-route
              d="M-20,320 C220,220 260,120 460,150 C660,180 700,60 900,90 C1040,110 1120,60 1230,40"
              stroke="#bfdbfe"
              strokeWidth={2}
              strokeLinecap="round"
              pathLength={1}
              strokeDasharray={1}
            />
          </svg>

          <div className="relative">
            <h2 className="font-display mx-auto max-w-xl text-3xl font-semibold text-white [text-wrap:balance] sm:text-5xl">
              See the fleet move.
            </h2>
            <p className="mx-auto mt-4 max-w-md text-blue-100/90">
              Open the dashboard and watch scattered stops resolve into routes your drivers can run.
            </p>
            <Button
              asChild
              size="lg"
              className="group mt-8 h-12 bg-white px-6 text-[15px] font-medium text-blue-700 shadow-lg transition-transform hover:-translate-y-0.5 hover:bg-blue-50"
            >
              <Link href="/dashboard">
                Open dashboard
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Standard multi-column footer. */}
      <div data-foot className="border-t border-slate-200">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="grid gap-12 md:grid-cols-[1.6fr_1fr_1fr_1fr]">
            {/* Brand */}
            <div data-fcol>
              <Link href="/" className="flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
                  <Truck className="h-4 w-4" strokeWidth={2.2} />
                </span>
                <span className="font-display text-lg font-semibold text-slate-950">FleetUp</span>
              </Link>
              <p className="mt-4 max-w-[34ch] text-sm leading-relaxed text-slate-600">
                Traffic-aware fleet route optimization that turns scattered stops into the fastest
                routes your drivers can actually run.
              </p>
            </div>

            {/* Link columns */}
            {columns.map((col) => (
              <div data-fcol key={col.title}>
                <h3 className="font-mono-ui text-xs uppercase tracking-wide text-slate-500">
                  {col.title}
                </h3>
                <ul className="mt-4 space-y-2.5">
                  {col.links.map((l) => (
                    <li key={l.label}>
                      <Link
                        href={l.href}
                        className="text-sm text-slate-600 transition-colors hover:text-slate-950"
                      >
                        {l.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Bottom bar */}
          <div className="mt-14 flex flex-col items-center justify-between gap-3 border-t border-slate-200 pt-6 sm:flex-row">
            <p className="text-sm text-slate-500">© 2025 FleetUp</p>
            <p className="font-mono-ui text-xs text-slate-500">
              live traffic · time windows · ML/RL routing
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
