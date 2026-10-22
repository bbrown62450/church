import type { Metadata, Viewport } from "next";
import { Figtree, Geist_Mono } from "next/font/google";

import { Toaster } from "@/components/ui/sonner";
import "./globals.css";
import { Providers } from "./providers";

const figtree = Figtree({ variable: "--font-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Worship Service Builder",
  description: "Plan Sunday worship services with your church.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // The browser bar takes the page's surface color in each mode (Theme PR 1).
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4fbf8" },
    { media: "(prefers-color-scheme: dark)", color: "#0e1513" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${figtree.variable} ${geistMono.variable}`}>
      <body className="antialiased">
        <Providers>{children}</Providers>
        <Toaster richColors />
      </body>
    </html>
  );
}
