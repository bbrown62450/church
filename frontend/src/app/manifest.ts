import type { MetadataRoute } from "next";

/**
 * The web manifest (Theme PR 1): the teal icon and the name when the app is
 * added to a home screen. The icon opens the app in the browser, as before
 * (owner, 2026-10-22), so `display` is "browser" and the layout sets no
 * Apple web-app meta.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Worship Service Builder",
    short_name: "Worship",
    description: "Plan Sunday worship services with your church.",
    start_url: "/builder",
    display: "browser",
    background_color: "#f4fbf8",
    theme_color: "#006a60",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
