import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// F §5.2: `npm test` runs both projects. Node for pure modules (*.test.ts);
// jsdom + Testing Library for components and layouts (*.test.tsx).
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: {
    // Node >= 25 defines its own localStorage/sessionStorage globals, which hide
    // jsdom's in the dom project (window.localStorage is undefined). CI's Node 22
    // accepts the flag; the feature is already off there.
    poolOptions: { forks: { execArgv: ["--no-experimental-webstorage"] } },
    projects: [
      {
        extends: true,
        test: { name: "unit", environment: "node", include: ["src/**/*.test.ts"] },
      },
      {
        extends: true,
        test: {
          name: "dom",
          environment: "jsdom",
          include: ["src/**/*.test.tsx"],
          setupFiles: ["src/test/setup-dom.ts"],
        },
      },
    ],
  },
});
