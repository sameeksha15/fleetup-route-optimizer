"use client";

import { useRef } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { ArrowRight } from "lucide-react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { SplitText } from "gsap/SplitText";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import { Button } from "@/components/ui/button";

const HeroMap = dynamic(() => import("./HeroMap"), { ssr: false });

export default function Hero() {
  const root = useRef<HTMLElement>(null);
  const backdrop = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      gsap.registerPlugin(SplitText, DrawSVGPlugin);
      const mm = gsap.matchMedia();

      mm.add("(prefers-reduced-motion: no-preference)", () => {
        // Masked, per-line headline reveal: the premium entrance.
        const split = new SplitText("[data-headline]", { type: "lines", mask: "lines" });

        const tl = gsap.timeline({ defaults: { ease: "expo.out" } });
        tl.from(split.lines, { yPercent: 120, duration: 1.15, stagger: 0.12 })
          .from("[data-sub]", { y: 20, opacity: 0, duration: 0.9 }, "-=0.75")
          .from("[data-mono]", { y: 14, opacity: 0, duration: 0.8 }, "-=0.6")
          .from("[data-cta]", { y: 16, opacity: 0, duration: 0.7, stagger: 0.1 }, "-=0.55")
          .from("[data-stat]", { y: 16, opacity: 0, duration: 0.7, stagger: 0.1 }, "-=0.5");

        // The route traces itself across the faint map; nodes settle in after.
        tl.from("[data-map]", { opacity: 0, duration: 1.6 }, 0)
          .fromTo(
            "#hero-route .route-line",
            { drawSVG: "0%" },
            { drawSVG: "100%", duration: 1.8, ease: "power2.inOut" },
            0.35,
          )
          .from("[data-node]", { scale: 0, opacity: 0, transformOrigin: "center", duration: 0.5, stagger: 0.12, ease: "back.out(1.7)" }, "-=0.7");

        // Demo metrics count up (real numbers from the demo run).
        root.current?.querySelectorAll<HTMLElement>("[data-count]").forEach((el) => {
          const to = parseFloat(el.dataset.count ?? "0");
          const dec = parseInt(el.dataset.dec ?? "0", 10);
          const suffix = el.dataset.suffix ?? "";
          const obj = { v: 0 };
          gsap.to(obj, {
            v: to,
            duration: 1.9,
            ease: "power1.out",
            delay: 0.7,
            onUpdate: () => {
              el.textContent = obj.v.toFixed(dec) + suffix;
            },
          });
        });

        // A slow, barely-there breath on the route glow: quiet life, not a toy.
        gsap.to("#hero-route .route-glow", {
          opacity: 0.5,
          duration: 3.4,
          ease: "sine.inOut",
          repeat: -1,
          yoyo: true,
          delay: 2,
        });

        // Depth: the backdrop drifts subtly with the pointer.
        const xTo = gsap.quickTo(backdrop.current, "x", { duration: 0.9, ease: "power3" });
        const yTo = gsap.quickTo(backdrop.current, "y", { duration: 0.9, ease: "power3" });
        const onMove = (e: PointerEvent) => {
          const r = root.current?.getBoundingClientRect();
          if (!r) return;
          xTo(((e.clientX - r.left) / r.width - 0.5) * -26);
          yTo(((e.clientY - r.top) / r.height - 0.5) * -18);
        };
        root.current?.addEventListener("pointermove", onMove);

        return () => {
          root.current?.removeEventListener("pointermove", onMove);
          split.revert();
        };
      });
    },
    { scope: root },
  );

  return (
    <section
      ref={root}
      className="relative flex min-h-screen items-center overflow-hidden bg-white"
    >
      {/* Backdrop: faint real map + cool-aurora gradient + traced route. Parallax layer. */}
      <div ref={backdrop} className="pointer-events-none absolute inset-0">
        {/* The real region, whisper-faint, masked away from the text column. */}
        <div
          data-map
          className="absolute inset-y-0 right-0 w-full opacity-[0.5] [mask-image:linear-gradient(to_left,black_25%,transparent_78%)] lg:w-[80%]"
        >
          <HeroMap />
        </div>

        {/* Cool aurora: blue, indigo, cyan, low and diffuse. */}
        <div className="absolute -right-[8%] -top-[10%] h-[620px] w-[620px] rounded-full bg-blue-500/20 blur-[130px]" />
        <div className="absolute right-[22%] top-[28%] h-[420px] w-[420px] rounded-full bg-indigo-500/15 blur-[120px]" />
        <div className="absolute right-[6%] bottom-[2%] h-[460px] w-[460px] rounded-full bg-cyan-400/15 blur-[120px]" />

        {/* The optimized route, drawn over the map as an elegant luminous line. */}
        <svg
          id="hero-route"
          className="absolute inset-y-0 right-0 hidden h-full w-[78%] md:block"
          viewBox="0 0 640 520"
          fill="none"
          preserveAspectRatio="xMidYMid slice"
          aria-hidden="true"
        >
          <defs>
            <filter id="heroRouteGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="7" />
            </filter>
          </defs>
          <path
            className="route-glow"
            d="M70,430 C170,360 150,250 280,250 C400,250 380,140 500,150 C560,155 580,120 600,96"
            stroke="#2563eb"
            strokeWidth={6}
            strokeLinecap="round"
            opacity={0.28}
            filter="url(#heroRouteGlow)"
          />
          <path
            className="route-line"
            d="M70,430 C170,360 150,250 280,250 C400,250 380,140 500,150 C560,155 580,120 600,96"
            stroke="#2563eb"
            strokeWidth={2.5}
            strokeLinecap="round"
          />
          {/* Depot + stop nodes: settle in, then hold. No pulsing. */}
          <g>
            <rect data-node x={62} y={422} width={16} height={16} rx={4} fill="#1e3a8a" />
            {[
              [280, 250],
              [500, 150],
              [600, 96],
            ].map(([x, y], i) => (
              <g key={i} data-node>
                <circle cx={x} cy={y} r={6.5} fill="#fff" stroke="#2563eb" strokeWidth={2.5} />
              </g>
            ))}
          </g>
        </svg>
      </div>

      {/* Keep the map/route from ever muddying the copy or the section seam. */}
      <div className="pointer-events-none absolute inset-y-0 left-0 w-full bg-gradient-to-r from-white via-white/70 to-transparent lg:w-[62%]" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-b from-transparent to-white" />

      {/* Foreground copy. */}
      <div className="relative z-10 mx-auto w-full max-w-6xl px-6">
        <div className="max-w-2xl">
          <h1
            data-headline
            className="font-display text-[clamp(2.25rem,6vw,5rem)] font-semibold leading-[1.03] text-slate-950 [text-wrap:balance]"
          >
            Every delivery, on its <span className="text-blue-600">best route</span>.
          </h1>

          <p data-sub className="mt-7 max-w-[46ch] text-lg leading-relaxed text-slate-600">
            FleetUp turns a day of scattered stops into the fastest routes your drivers can
            actually run, sequenced against live traffic in one pass.
          </p>

          <p
            data-mono
            className="font-mono-ui mt-5 text-[13px] uppercase tracking-wide text-slate-500"
          >
            live traffic · time windows · driver shifts
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Button
              asChild
              size="lg"
              data-cta
              className="group h-12 bg-blue-600 px-6 text-[15px] text-white shadow-[0_10px_30px_-10px_rgba(37,99,235,0.6)] transition-all hover:-translate-y-0.5 hover:bg-blue-700"
            >
              <Link href="/dashboard">
                Open dashboard
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </Button>
            <Button
              asChild
              variant="ghost"
              size="lg"
              data-cta
              className="h-12 px-5 text-[15px] text-slate-700 hover:bg-slate-100 hover:text-slate-950"
            >
              <Link href="#how">See how it works</Link>
            </Button>
          </div>

          {/* Real numbers from the demo run: quiet proof, counting up. */}
          <div className="mt-12 flex items-center gap-7">
            <div data-stat>
              <div className="font-display text-2xl font-semibold text-slate-950">
                <span data-count="98.9" data-dec="1" data-suffix="%">
                  98.9%
                </span>
              </div>
              <div className="font-mono-ui mt-0.5 text-xs text-slate-500">on-time</div>
            </div>
            <div className="h-9 w-px bg-slate-200" />
            <div data-stat>
              <div className="font-display text-2xl font-semibold text-slate-950">
                <span data-count="248" data-suffix=" km">
                  248 km
                </span>
              </div>
              <div className="font-mono-ui mt-0.5 text-xs text-slate-500">routed today</div>
            </div>
            <div className="hidden h-9 w-px bg-slate-200 sm:block" />
            <div data-stat className="hidden sm:block">
              <div className="font-display text-2xl font-semibold text-slate-950">
                <span data-count="9" data-suffix=" trucks">
                  9 trucks
                </span>
              </div>
              <div className="font-mono-ui mt-0.5 text-xs text-slate-500">one run</div>
            </div>
          </div>
        </div>
      </div>

      {/* Basemap attribution (Carto + OSM), kept quiet. */}
      <span className="font-mono-ui absolute bottom-2 right-3 z-10 text-[10px] text-slate-400">
        © OpenStreetMap · CARTO
      </span>
    </section>
  );
}
