import { readFileSync } from "node:fs";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { testDraft } from "@/test/fixtures";

import {
  bulletinEmailBody,
  bulletinEmailSubject,
  clearUncertainSend,
  countRecipients,
  defaultBulletinMessage,
  emailPrefsKey,
  fieldTarget,
  parseAddressList,
  parseReopen,
  readEmailPrefs,
  readUncertainSend,
  uncertainSendKey,
  writeEmailPrefs,
  writeUncertainSend,
} from "./email";

type Case = { date_iso: string; subject: string; default_message: string };
const { cases } = JSON.parse(
  readFileSync(new URL("../../../backend/tests/fixtures/shared/bulletin_email.json", import.meta.url), "utf-8"),
) as { cases: Case[] };

let data: Map<string, string>;

beforeEach(() => {
  data = new Map();
  const storage = {
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => void data.set(k, v),
    removeItem: (k: string) => void data.delete(k),
  };
  vi.stubGlobal("window", { localStorage: storage, sessionStorage: storage });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the bulletin email (slice 5b-2)", () => {
  it("writes the subject and the default message as the server does (shared/bulletin_email.json)", () => {
    expect(cases).toHaveLength(6);
    for (const c of cases) {
      expect(bulletinEmailSubject(c.date_iso), c.date_iso).toBe(c.subject);
      expect(defaultBulletinMessage(c.date_iso), c.date_iso).toBe(c.default_message);
    }
  });

  it("reads Other addresses split on commas, semicolons and new lines", () => {
    expect(parseAddressList(" a@example.org, b@example.org;c@example.org\n\nMary Jones <mary@example.org> ,, ")).toEqual([
      "a@example.org",
      "b@example.org",
      "c@example.org",
      "mary@example.org",
    ]);
    expect(parseAddressList("   ")).toEqual([]);
  });

  it("counts each person once, ignoring capitals and spaces", () => {
    expect(countRecipients(["mary@example.org", "office@example.org"], ["MARY@example.org ", "organist@example.org"])).toBe(3);
    expect(countRecipients([], [])).toBe(0);
  });

  it("puts each field's message where it belongs", () => {
    expect(["additional_emails", "additional_emails.3"].map(fieldTarget)).toEqual(["other", "other"]);
    expect(fieldTarget("message")).toBe("message");
    expect(fieldTarget("attachments")).toBe("attachments");
    expect(["recipients", "contact_ids", "contact_ids.2"].map(fieldTarget)).toEqual(["to", "to", "to"]);
    expect(["custom_elements.0.label", "service.service_date_iso", "translation"].map(fieldTarget)).toEqual(["top", "top", "top"]);
  });

  it("remembers the last send's contacts and the attachments per user and church", () => {
    expect(readEmailPrefs("u1", "c1")).toEqual({ version: 1, contact_ids: [], attachments: ["docx"] });
    writeEmailPrefs("u1", "c1", { attachments: ["pdf", "docx"] });
    writeEmailPrefs("u1", "c1", { contact_ids: ["k1", "k2"] });
    expect(readEmailPrefs("u1", "c1")).toEqual({ version: 1, contact_ids: ["k1", "k2"], attachments: ["docx", "pdf"] });
    expect(readEmailPrefs("u1", "c2").contact_ids).toEqual([]);
    expect(emailPrefsKey("u1", "c1")).toBe("wsb:emailPrefs:u1:c1");
    data.set(emailPrefsKey("u1", "c3"), JSON.stringify({ version: 1, contact_ids: "k1", attachments: [] }));
    expect(readEmailPrefs("u1", "c3")).toEqual({ version: 1, contact_ids: [], attachments: ["docx"] });
    data.set(emailPrefsKey("u1", "c4"), "{broken");
    expect(readEmailPrefs("u1", "c4").attachments).toEqual(["docx"]);
  });

  it("remembers a send that may already have gone out, per user and church, in this tab", () => {
    expect(readUncertainSend("u1", "c1")).toBeNull();
    writeUncertainSend("u1", "c1", "Check your Gmail Sent folder before sending again.");
    expect(readUncertainSend("u1", "c1")).toBe("Check your Gmail Sent folder before sending again.");
    expect(readUncertainSend("u1", "c2")).toBeNull();
    expect(uncertainSendKey("u1", "c1")).toBe("wsb:emailUncertain:u1:c1");
    data.set(uncertainSendKey("u1", "c3"), "{broken");
    expect(readUncertainSend("u1", "c3")).toBeNull();
    clearUncertainSend("u1", "c1");
    expect(readUncertainSend("u1", "c1")).toBeNull();
  });

  it("sends the service as the downloads do, with the choices and the draft's translation", () => {
    const draft = testDraft((d) => ({ ...d, readings: { ...d.readings, translation: "nrsvue" } }));
    const body = bulletinEmailBody(draft, {
      contactIds: ["k1"],
      otherAddresses: "organist@example.org; ",
      message: "See you Sunday.",
      attachments: ["pdf", "docx"],
    });
    expect(body).toMatchObject({
      contact_ids: ["k1"],
      additional_emails: ["organist@example.org"],
      message: "See you Sunday.",
      attachments: ["docx", "pdf"],
      translation: "nrsvue",
    });
    expect(body.service.service_date_iso).toBe(draft.readings.date_iso);
  });

  it("reopens the dialog only for the same church", () => {
    const raw = JSON.stringify({ church_id: "c1", contact_ids: ["k1"], other_addresses: "a@example.org", message: "Hi", attachments: ["pdf"] });
    expect(parseReopen(raw, "c1")).toEqual({ church_id: "c1", contact_ids: ["k1"], other_addresses: "a@example.org", message: "Hi", attachments: ["pdf"] });
    expect(parseReopen(JSON.stringify({ church_id: "c1" }), "c1")).toEqual({ church_id: "c1" });
    expect(parseReopen(raw, "c2")).toBeNull();
    expect(parseReopen("{broken", "c1")).toBeNull();
    expect(parseReopen(null, "c1")).toBeNull();
  });
});
