export type Church = { id: string; name: string; role: "owner" | "admin" | "member" };

export type Me = {
  user: { id: string; email: string; name: string | null; picture: string | null };
  churches: Church[];
};

const ACTIVE_CHURCH_KEY = "activeChurchId";

/** The remembered church if the user still belongs to it, else their first church. */
export function pickActiveChurch(churches: Church[], storedId: string | null): Church | null {
  return churches.find((c) => c.id === storedId) ?? churches[0] ?? null;
}

export function readStoredChurchId(): string | null {
  try {
    return window.localStorage.getItem(ACTIVE_CHURCH_KEY);
  } catch {
    return null;
  }
}

export function storeChurchId(id: string | null): void {
  try {
    if (id) window.localStorage.setItem(ACTIVE_CHURCH_KEY, id);
    else window.localStorage.removeItem(ACTIVE_CHURCH_KEY);
  } catch {
    // Storage unavailable (e.g. private mode): the choice just won't be remembered.
  }
}
