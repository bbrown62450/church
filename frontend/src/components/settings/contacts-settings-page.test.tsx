/**
 * Settings → Contacts (slice 5b-1; 6a spec "Contacts"): every member reads
 * the list, admins add, edit and delete. Rendered inside the Settings layout,
 * as the route is, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import ContactsSettingsRoute from "@/app/(signed-in)/(church)/settings/contacts/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Contact } from "@/lib/api/types";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, contact, contactList, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { ADMINS_ONLY, CONTACTS_INTRO, INVALID_ADDRESS_ADMIN, INVALID_ADDRESS_MEMBER } from "./contacts-settings-page";

afterEach(() => {
  toast.dismiss();
});

const BROKEN = contact({ id: "6c0b5e1a-1d2b-4c3d-8e4f-5a6b7c8d9e03", name: "Two at once", email: "a@example.org, b@example.org", email_valid: false });

/** A fake `/contacts`: `GET` answers with what the writes left, as the server would after a refetch. */
function contactsServer(initial: Contact[] = contactList().items) {
  let items = [...initial];
  return {
    list: () => contactList(items),
    add: (added: Contact) => {
      items = [...items, added];
      return { status: 201, body: added };
    },
    save: (saved: Contact) => {
      items = items.map((c) => (c.id === saved.id ? saved : c));
      return saved;
    },
    remove: (id: string) => {
      items = items.filter((c) => c.id !== id);
      return { deleted: true };
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({ "GET /contacts": contactList(), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <ContactsSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/contacts" },
  );
  return { ...view, api };
}

function writes(api: { requests: RecordedRequest[] }, method: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith("/contacts"));
}

function rows() {
  return within(screen.getByRole("list", { name: "Contacts" })).getAllByRole("listitem");
}

describe("Settings → Contacts (slice 5b-1)", () => {
  it("shows a member the list as text, with the note, a flag on a bad address, and no controls", async () => {
    renderPage("member", { "GET /contacts": contactList([contact(), contact({ id: "c-2", name: null, email: "office@example.org" }), BROKEN]) });
    expect(await screen.findByText("Mary Jones")).toBeInTheDocument();
    expect(screen.getByText(CONTACTS_INTRO)).toBeInTheDocument();
    expect(screen.getByText(ADMINS_ONLY)).toBeInTheDocument();
    expect(rows().map((row) => row.textContent)).toEqual([
      "Mary Jonesmary@example.org",
      "office@example.org",
      `Two at oncea@example.org, b@example.org${INVALID_ADDRESS_MEMBER}`,
    ]);
    expect(screen.queryByRole("button", { name: /^(Edit|Delete) / })).toBeNull();
    expect(screen.queryByRole("button", { name: "Add contact" })).toBeNull();
    expect(screen.queryAllByRole("textbox")).toEqual([]);
  });

  it("lets an admin add a contact: the row appears, the fields clear and Name has focus", async () => {
    const added = contact({ id: "c-new", name: "Sam Sample", email: "sam@example.org" });
    const server = contactsServer();
    const { api, user } = renderPage("admin", { "GET /contacts": server.list, "POST /contacts": () => server.add(added) });
    await screen.findByText("Mary Jones");
    const name = screen.getByLabelText("Name (optional)");
    const email = screen.getByLabelText("Email");
    await user.type(name, " Sam Sample ");
    await user.type(email, " sam@example.org ");
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(await screen.findByText("Sam Sample")).toBeInTheDocument();
    expect(writes(api, "POST")[0].body).toEqual({ name: "Sam Sample", email: "sam@example.org" });
    expect(writes(api, "POST")[0].headers["x-church-id"]).toBe(church().id);
    expect(rows()).toHaveLength(3);
    expect(name).toHaveValue("");
    expect(email).toHaveValue("");
    await waitFor(() => expect(name).toHaveFocus());
  });

  it("says what is wrong with an address under Email and focuses it", async () => {
    const { api, user } = renderPage("admin", {
      "POST /contacts": fakeError(409, "conflict", "That email is already in your contacts."),
    });
    await screen.findByText("Mary Jones");
    const email = screen.getByLabelText("Email");
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Email is required.");
    expect(writes(api, "POST")).toHaveLength(0);
    await user.type(email, "MARY@example.org");
    expect(screen.queryByRole("alert")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(await screen.findByText("That email is already in your contacts.")).toBeInTheDocument();
    expect(email).toHaveAttribute("aria-invalid", "true");
    await waitFor(() => expect(email).toHaveFocus());
    expect(email).toHaveValue("MARY@example.org");

    api.set("POST /contacts", fakeError(422, "invalid_request", "Enter a valid email address.", { fields: { email: "Enter a valid email address." } }));
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
  });

  it("lets an admin edit a contact: only the changed field is sent and the row shows the answer", async () => {
    const server = contactsServer();
    const { api, user } = renderPage("admin", {
      "GET /contacts": server.list,
      [`PATCH /contacts/${contact().id}`]: (r: RecordedRequest) => server.save({ ...contact(), ...(r.body as Partial<Contact>) }),
    });
    await user.click(await screen.findByRole("button", { name: "Edit Mary Jones" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit contact" });
    const name = within(dialog).getByLabelText("Name (optional)");
    await user.clear(name);
    await user.type(name, "Mary Smith");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(writes(api, "PATCH")[0].body).toEqual({ name: "Mary Smith" });
    expect(rows()[0]).toHaveTextContent("Mary Smithmary@example.org");
  });

  it("shows an edit's 409 in the dialog, and Cancel leaves the contact as it was", async () => {
    const { api, user } = renderPage("admin", {
      [`PATCH /contacts/${contact().id}`]: fakeError(409, "conflict", "That email is already in your contacts."),
    });
    await user.click(await screen.findByRole("button", { name: "Edit Mary Jones" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit contact" });
    const email = within(dialog).getByLabelText("Email");
    await user.clear(email);
    await user.type(email, "office@example.org");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await within(dialog).findByText("That email is already in your contacts.")).toBeInTheDocument();
    expect(writes(api, "PATCH")[0].body).toEqual({ email: "office@example.org" });
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(rows()[0]).toHaveTextContent("Mary Jonesmary@example.org");
  });

  it("asks before deleting, then removes the row; focus goes back to the bin on Cancel, to Name after a delete", async () => {
    const server = contactsServer();
    const office = server.list().items[1];
    const { api, user } = renderPage("admin", {
      "GET /contacts": server.list,
      [`DELETE /contacts/${office.id}`]: () => server.remove(office.id),
    });
    const bin = await screen.findByRole("button", { name: "Delete office@example.org" });
    await user.click(bin);
    let confirm = await screen.findByRole("alertdialog", { name: "Delete office@example.org?" });
    await user.click(within(confirm).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    await waitFor(() => expect(bin).toHaveFocus());
    await user.click(bin);
    confirm = await screen.findByRole("alertdialog", { name: "Delete office@example.org?" });
    expect(confirm).toHaveTextContent("They won't be offered as a bulletin recipient anymore.");
    await user.click(within(confirm).getByRole("button", { name: "Delete contact" }));
    await waitFor(() => expect(screen.queryByText("office@example.org")).toBeNull());
    expect(writes(api, "DELETE")).toHaveLength(1);
    expect(rows()).toHaveLength(1);
    await waitFor(() => expect(screen.getByLabelText("Name (optional)")).toHaveFocus());
  });

  it("closes the edit dialog when the contact was deleted elsewhere, says so and refetches the list", async () => {
    const server = contactsServer();
    const mary = contact();
    const { api, user } = renderPage("admin", {
      "GET /contacts": server.list,
      [`PATCH /contacts/${mary.id}`]: () => {
        server.remove(mary.id); // deleted in another tab meanwhile
        return fakeError(404, "not_found", "Contact not found.");
      },
    });
    await user.click(await screen.findByRole("button", { name: "Edit Mary Jones" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit contact" });
    await user.type(within(dialog).getByLabelText("Name (optional)"), " Smith");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Contact not found.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(screen.queryByText("Mary Jones")).toBeNull());
    expect(writes(api, "GET").length).toBeGreaterThan(1);
    expect(rows()).toHaveLength(1);
    // the row and its pencil are gone, so focus goes to the add form's Name, not the page
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText("Name (optional)")));
  });

  it("treats a delete of a contact already deleted elsewhere as done: the row goes and Name has focus", async () => {
    const server = contactsServer();
    const office = server.list().items[1];
    const { user } = renderPage("admin", {
      "GET /contacts": server.list,
      [`DELETE /contacts/${office.id}`]: () => {
        server.remove(office.id); // deleted in another tab meanwhile
        return fakeError(404, "not_found", "Contact not found.");
      },
    });
    await user.click(await screen.findByRole("button", { name: "Delete office@example.org" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Delete office@example.org?" });
    await user.click(within(confirm).getByRole("button", { name: "Delete contact" }));
    expect(await screen.findByText("Contact not found.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    await waitFor(() => expect(screen.queryByText("office@example.org")).toBeNull());
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText("Name (optional)")));
  });

  it("toasts a refusal that names no field of the form, and leaves the fields as typed", async () => {
    const { user } = renderPage("admin", {
      "POST /contacts": fakeError(422, "invalid_request", "The request was not valid.", {
        fields: { church_id: "Not a valid value." },
      }),
    });
    const email = await screen.findByLabelText("Email");
    await user.type(email, "sam@example.org");
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(await screen.findByText("The request was not valid.")).toBeInTheDocument();
    expect(email).not.toHaveAttribute("aria-invalid");
    expect(email).toHaveValue("sam@example.org");
  });

  it("flags a saved address the send-time check refuses, and the admin fixes it", async () => {
    const fixed = { ...BROKEN, email: "a@example.org", email_valid: true };
    const server = contactsServer([BROKEN]);
    const { user } = renderPage("admin", { "GET /contacts": server.list, [`PATCH /contacts/${BROKEN.id}`]: () => server.save(fixed) });
    expect(await screen.findByText(INVALID_ADDRESS_ADMIN)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Edit Two at once" }));
    const email = within(await screen.findByRole("dialog")).getByLabelText("Email");
    await user.clear(email);
    await user.type(email, "a@example.org{Enter}");
    await waitFor(() => expect(screen.queryByText(INVALID_ADDRESS_ADMIN)).toBeNull());
  });

  it("shows each role its empty state", async () => {
    const { unmount } = renderPage("admin", { "GET /contacts": contactList([]) });
    expect(await screen.findByText("Add the people who receive the bulletin, like your church secretary.")).toBeInTheDocument();
    expect(screen.getByText("No contacts yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add contact" })).toBeInTheDocument();
    unmount();
    renderPage("member", { "GET /contacts": contactList([]) });
    expect(await screen.findByText("Ask an admin to add bulletin recipients.")).toBeInTheDocument();
  });

  it("asks before leaving with something typed in the add form", async () => {
    const { user } = renderPage("admin");
    await user.type(await screen.findByLabelText("Email"), "sam@example.org");
    await user.click(screen.getByRole("link", { name: "Church" }));
    const dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/settings/church");
  });

  it("toasts a role 403 and refetches the church profile, so the page turns read-only", async () => {
    const { user, queryClient } = renderPage("admin", {
      "POST /contacts": fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.type(await screen.findByLabelText("Email"), "sam@example.org");
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
  });

  it("shows the error state with Retry when the list cannot be read", async () => {
    renderPage("admin", { "GET /contacts": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
