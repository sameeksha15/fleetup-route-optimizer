/** The signature hero motif: depots, delivery stops, and two trucks gliding
 *  along live routes: a miniature of the actual dashboard map. */
export default function RouteAnimation() {
  return (
    <svg
      viewBox="0 0 420 320"
      className="h-full w-full"
      role="img"
      aria-label="Animated map of delivery routes"
    >
      <defs>
        <pattern id="lp-grid" width="28" height="28" patternUnits="userSpaceOnUse">
          <circle cx="1.5" cy="1.5" r="1.5" fill="rgba(148,163,184,0.18)" />
        </pattern>
        <linearGradient id="lp-blue" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#60a5fa" />
          <stop offset="1" stopColor="#2563eb" />
        </linearGradient>
      </defs>

      <rect x="0" y="0" width="420" height="320" fill="url(#lp-grid)" />

      {/* Route paths (referenced by the moving trucks below). */}
      <path
        id="lp-routeA"
        d="M60,250 C130,210 150,120 240,140 C300,152 340,110 384,88"
        fill="none"
        stroke="url(#lp-blue)"
        strokeWidth="3"
        strokeLinecap="round"
        className="lp-route"
        opacity="0.9"
      />
      <path
        id="lp-routeB"
        d="M60,250 C110,272 196,258 236,226 C292,188 332,214 376,236"
        fill="none"
        stroke="#34d399"
        strokeWidth="3"
        strokeLinecap="round"
        className="lp-route lp-route--slow"
        opacity="0.85"
      />

      {/* Delivery stops. */}
      {[
        [240, 140],
        [384, 88],
        [236, 226],
        [376, 236],
      ].map(([cx, cy], i) => (
        <g key={i}>
          <circle cx={cx} cy={cy} r="9" fill={i < 2 ? "#3b82f6" : "#10b981"} opacity="0.25" className="lp-pulse" />
          <circle cx={cx} cy={cy} r="4.5" fill={i < 2 ? "#3b82f6" : "#10b981"} stroke="#fff" strokeWidth="1.5" />
        </g>
      ))}

      {/* Depot. */}
      <g>
        <rect x="48" y="238" width="24" height="24" rx="6" fill="#0f172a" stroke="#fff" strokeWidth="2" />
        <rect x="55" y="245" width="10" height="10" rx="1.5" fill="#38bdf8" />
      </g>

      {/* Trucks gliding along the routes. */}
      <circle r="5.5" fill="#fff" stroke="#2563eb" strokeWidth="2.5">
        <animateMotion dur="7s" repeatCount="indefinite" rotate="auto">
          <mpath href="#lp-routeA" />
        </animateMotion>
      </circle>
      <circle r="5.5" fill="#fff" stroke="#10b981" strokeWidth="2.5">
        <animateMotion dur="9s" repeatCount="indefinite" rotate="auto">
          <mpath href="#lp-routeB" />
        </animateMotion>
      </circle>
    </svg>
  );
}
