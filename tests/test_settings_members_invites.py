import pytest


def test_member_rejected_by_action_helpers(tmp_db, make_user, make_church):
    from views.settings import (
        apply_role_change, apply_remove_member, do_create_invite,
        do_revoke_invite, NotAuthorizedError,
    )
    from repos.memberships import add_membership
    owner = make_user(email="o@c.org")
    church = make_church(name="C", timezone="America/New_York", owner_user_id=owner)
    m1 = make_user(email="m1@c.org"); add_membership(m1, church, "member")
    m2 = make_user(email="m2@c.org"); add_membership(m2, church, "member")
    with pytest.raises(NotAuthorizedError):
        apply_role_change(m1, church, m2, "admin")
    with pytest.raises(NotAuthorizedError):
        apply_remove_member(m1, church, m2)
    with pytest.raises(NotAuthorizedError):
        do_create_invite(m1, church)
    with pytest.raises(NotAuthorizedError):
        do_revoke_invite(m1, church, "any-id")


def test_remove_last_admin_surfaces_lastadmin_error(tmp_db, make_user, make_church):
    from views.settings import apply_remove_member
    from repos.memberships import LastAdminError
    owner = make_user(email="o@d.org")
    church = make_church(name="D", timezone="America/New_York", owner_user_id=owner)
    with pytest.raises(LastAdminError):
        apply_remove_member(owner, church, owner)  # owner is the last admin


def test_owner_only_transfer_and_delete(tmp_db, make_user, make_church):
    from views.settings import transfer_ownership, delete_this_church, NotAuthorizedError
    from repos.memberships import add_membership, get_role
    owner = make_user(email="o@e.org")
    church = make_church(name="E", timezone="America/New_York", owner_user_id=owner)
    admin = make_user(email="a@e.org"); add_membership(admin, church, "admin")
    # An admin (not owner) is rejected by the owner-only helpers.
    with pytest.raises(NotAuthorizedError):
        transfer_ownership(admin, church, owner)
    with pytest.raises(NotAuthorizedError):
        delete_this_church(admin, church)
    # The owner can transfer: new owner becomes 'owner', old owner demoted to 'admin'.
    transfer_ownership(owner, church, admin)
    assert get_role(admin, church) == "owner"
    assert get_role(owner, church) == "admin"


def test_admin_can_create_invite(tmp_db, make_user, make_church):
    from views.settings import do_create_invite
    owner = make_user(email="o@k.org")
    church = make_church(name="K", timezone="America/New_York", owner_user_id=owner)
    code = do_create_invite(owner, church, role="member")
    assert isinstance(code, str) and len(code) >= 20
