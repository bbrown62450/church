"""The suite never reaches the network (F §5.3): conftest's autouse _no_network
fixture refuses any socket connect that is not to this machine."""
import socket

import pytest


def test_an_outbound_connect_raises():
    # 192.0.2.1 is TEST-NET-1 (RFC 5737): a numeric address, so no DNS lookup either.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)          # if the guard were ever missing: fail in 1 s, never hang
        with pytest.raises(RuntimeError, match="Tests must not open network connections: 192.0.2.1"):
            sock.connect(("192.0.2.1", 80))

    # libpq opens its own sockets: the guard checks psycopg2's host too.
    from sqlalchemy import create_engine
    engine = create_engine("postgresql+psycopg2://u:p@aws-0-us-east-1.pooler.supabase.com:5432/postgres")
    with pytest.raises(RuntimeError, match="Tests must not open network connections: aws-0-us-east-1.pooler.supabase.com"):
        engine.connect()


def test_a_localhost_connect_is_allowed():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.create_connection(server.getsockname(), timeout=5) as client:
            peer, _ = server.accept()
            with peer:
                client.sendall(b"ping")
                assert peer.recv(4) == b"ping"
