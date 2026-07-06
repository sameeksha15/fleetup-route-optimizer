"use client";

import { useRef } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { ScrollTrigger } from "gsap/ScrollTrigger";

const steps = [
  {
    label: "Add your stops",
    body: "Enter deliveries by hand, or import the spreadsheet you already keep. Warehouses, windows, parcel sizes.",
  },
  {
    label: "Optimize",
    body: "One run clusters, sequences, and packs every truck against live road times, comparing heuristic and learned policy side by side.",
  },
  {
    label: "Track it live",
    body: "Follow each route on the map, stop by stop, with ETAs, on-time status, and reload waves as trucks return.",
  },
];

const solves = ["Live traffic", "Time windows", "Driver shifts", "Parcel fit", "Multi-trip waves"];

export default function Features() {
  const root = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      gsap.registerPlugin(ScrollTrigger);
      const mm = gsap.matchMedia();

      mm.add("(prefers-reduced-motion: no-preference)", () => {
        const tl = gsap.timeline({
          defaults: { ease: "expo.out" },
          scrollTrigger: { trigger: root.current, start: "top 72%", once: true },
        });

        tl.from("[data-fh]", { y: 26, opacity: 0, duration: 0.9 })
          // The route between the stops draws itself as you arrive.
          .from("[data-line-h]", { scaleX: 0, transformOrigin: "left center", duration: 1.1, ease: "power2.inOut" }, "-=0.4")
          .from("[data-line-v]", { scaleY: 0, transformOrigin: "top center", duration: 1.1, ease: "power2.inOut" }, "<")
          .from("[data-step]", { y: 24, opacity: 0, duration: 0.8, stagger: 0.16 }, "-=0.85")
          .from("[data-node]", { scale: 0, opacity: 0, transformOrigin: "center", duration: 0.5, stagger: 0.16, ease: "back.out(1.7)" }, "-=0.95")
          .from("[data-chip]", { y: 12, opacity: 0, duration: 0.5, stagger: 0.06 }, "-=0.3");
      });
    },
    { scope: root },
  );

  return (
    <section
      ref={root}
      id="how"
      className="relative overflow-hidden bg-white px-6 py-28 sm:py-36"
    >
      {/* Cool aurora, placed low-left so it differs from the hero. */}
      <div className="pointer-events-none absolute -left-[6%] top-[20%] h-[460px] w-[460px] rounded-full bg-indigo-500/10 blur-[130px]" />
      <div className="pointer-events-none absolute left-[38%] -bottom-[10%] h-[420px] w-[420px] rounded-full bg-cyan-400/10 blur-[120px]" />

      <div className="relative mx-auto max-w-5xl">
        <h2
          data-fh
          className="font-display max-w-xl text-3xl font-semibold leading-tight text-slate-950 [text-wrap:balance] sm:text-[2.75rem]"
        >
          From stops to a plan in one run.
        </h2>

        {/* Three stops on one route: a real sequence, so the line carries meaning. */}
        <div className="relative mt-16">
          {/* Desktop: horizontal route line behind the nodes. */}
          <div
            data-line-h
            className="pointer-events-none absolute left-0 right-0 top-[7px] hidden h-px bg-gradient-to-r from-blue-400 via-blue-300 to-transparent sm:block"
          />
          {/* Mobile: vertical route rail connecting the stacked stops. */}
          <div
            data-line-v
            className="pointer-events-none absolute bottom-10 left-[6px] top-2 w-px bg-gradient-to-b from-blue-400 via-blue-300 to-transparent sm:hidden"
          />

          <div className="grid gap-12 sm:grid-cols-3 sm:gap-8">
            {steps.map((s) => (
              <div data-step key={s.label} className="relative pl-8 sm:pl-0 sm:pt-9">
                <span
                  data-node
                  className="absolute left-0 top-0 h-3.5 w-3.5 rounded-full bg-blue-600 shadow-[0_0_0_4px_#fff]"
                />
                <h3 className="font-display text-lg font-semibold text-slate-950">{s.label}</h3>
                <p className="mt-2 max-w-[36ch] text-[15px] leading-relaxed text-slate-600">
                  {s.body}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* The intrigue: what a single run actually reconciles. */}
        <div className="mt-20 flex flex-wrap items-center gap-2">
          <span className="font-mono-ui mr-2 text-xs uppercase tracking-wide text-slate-500">
            one run reconciles
          </span>
          {solves.map((c) => (
            <span
              data-chip
              key={c}
              className="rounded-full bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200"
            >
              {c}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
