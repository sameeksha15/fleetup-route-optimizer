import type { Metadata } from "next";
import { Geist, Geist_Mono, Archivo } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/components/auth/AuthProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Engineered grotesque for landing display headings only. Deliberately not
// Inter/Geist-by-reflex; it gives the brand surface a technical, precise voice
// while the product UI keeps Geist. Variable font: weight set in CSS.
const archivo = Archivo({
  variable: "--font-display",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FleetUp: Traffic-Aware Fleet Route Optimization",
  description:
    "FleetUp plans multi-trip delivery routes with live traffic, driver realism, and ML/RL optimization.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${archivo.variable} antialiased`}
      >
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
