import path from "node:path";
import { fileURLToPath } from "node:url";
import { ESLint } from "eslint";
import { expect, it } from "vitest";

// frontend/, so ESLint loads the project's eslint.config.mjs.
const FRONTEND_ROOT = fileURLToPath(new URL("../..", import.meta.url));

const PROBE = `export function Probe({ html }: { html: string }) {
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
`;

it("reports dangerouslySetInnerHTML as a react/no-danger error (F §4.9)", async () => {
  const eslint = new ESLint({ cwd: FRONTEND_ROOT });
  const [result] = await eslint.lintText(PROBE, {
    // Never written to disk; the path only selects the config for a .tsx file under src/.
    filePath: path.join(FRONTEND_ROOT, "src", "components", "lint-probe.tsx"),
  });
  const noDanger = result.messages.filter((message) => message.ruleId === "react/no-danger");
  expect(noDanger).toHaveLength(1);
  expect(noDanger[0].severity).toBe(2);
}, 30_000);
