/**
 * Auth events (F §4.4, §4.2): `handleAuthErrors` in ./client emits them from the
 * query and mutation caches; the layouts subscribe. `(signed-in)` signs out on
 * `signOutRequired` (Task 22); `(church)` falls back to the next church on
 * `churchAccessLost` (Task 23). Listeners run synchronously, in subscription order.
 */
type SignOutListener = () => void;
type ChurchAccessLostListener = (churchId: string) => void;

const signOutListeners = new Set<SignOutListener>();
const churchAccessLostListeners = new Set<ChurchAccessLostListener>();

export const authEvents = {
  /** An API call answered 401: the session is gone or was rejected. */
  signOutRequired(): void {
    for (const listener of [...signOutListeners]) listener();
  },

  /** A church-scoped call answered 403 with `details.reason = "no_church_access"`. */
  churchAccessLost(churchId: string): void {
    for (const listener of [...churchAccessLostListeners]) listener(churchId);
  },

  /** Returns the unsubscribe function (an effect's cleanup). */
  onSignOutRequired(listener: SignOutListener): () => void {
    signOutListeners.add(listener);
    return () => {
      signOutListeners.delete(listener);
    };
  },

  /** Returns the unsubscribe function (an effect's cleanup). */
  onChurchAccessLost(listener: ChurchAccessLostListener): () => void {
    churchAccessLostListeners.add(listener);
    return () => {
      churchAccessLostListeners.delete(listener);
    };
  },
};
