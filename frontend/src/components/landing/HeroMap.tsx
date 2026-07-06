"use client";

// Ambient backdrop only: a real service region as a faint texture behind the
// hero. Light Carto Positron basemap (fades to a whisper, unlike full-colour
// OSM), fully non-interactive. The elegant route motif is drawn as an SVG
// overlay in Hero; this layer just grounds the page in a real place.

import { useEffect } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

function Frame() {
  const map = useMap();
  useEffect(() => {
    // Frame the operating region and hold (map is static).
    map.fitBounds(
      [
        [19.32, 72.77],
        [18.97, 73.06],
      ],
      { padding: [0, 0], animate: false },
    );
  }, [map]);
  return null;
}

export default function HeroMap() {
  return (
    <MapContainer
      center={[19.11, 72.92]}
      zoom={11}
      className="h-full w-full bg-transparent"
      dragging={false}
      scrollWheelZoom={false}
      doubleClickZoom={false}
      touchZoom={false}
      keyboard={false}
      zoomControl={false}
      attributionControl={false}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
        subdomains="abcd"
      />
      <Frame />
    </MapContainer>
  );
}
