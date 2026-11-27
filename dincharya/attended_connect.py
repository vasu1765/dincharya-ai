"""Attended CONNECT relay. The operator retains both TLS endpoints and CA checks."""
import asyncio
import ipaddress
import sys

OPERATOR = "172.29.241.2"
LISTENER = "172.29.241.3"
PORT = 8443
AUTHORITY = b"api.telegram.org:443"
PROXY = f"http://{LISTENER}:{PORT}"


def upstream(value):
    ip = ipaddress.IPv4Address(value)
    if not ip.is_global or ip.is_multicast or str(ip) != value:
        raise ValueError("Expected one approved public unicast IPv4 address")
    return str(ip)


def permitted(data):
    lines = data.split(b"\r\n")
    if lines[0] != b"CONNECT "+AUTHORITY+b" HTTP/1.1" or lines[-2:] != [b"", b""]:
        return False
    headers = {}
    for line in lines[1:-2]:
        name, sep, value = line.partition(b":")
        name = name.lower()
        if not sep or name in headers or name not in (b"host", b"accept"):
            return False
        headers[name] = value.strip(b" ")
    return headers.get(b"host") == AUTHORITY and headers.get(b"accept",b"*/*") == b"*/*"


async def pump(reader, writer):
    while chunk := await reader.read(16384):
        writer.write(chunk)
        await writer.drain()


async def tunnel(reader, client, destination):
    remote = None
    streams = []
    try:
        if client.get_extra_info("peername")[0] != OPERATOR:
            return
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 3)
        if not permitted(head):
            client.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            await client.drain()
            return
        incoming, remote = await asyncio.wait_for(asyncio.open_connection(destination,443),4)
        client.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await client.drain()
        streams = [asyncio.create_task(pump(reader,remote)),asyncio.create_task(pump(incoming,client))]
        await asyncio.wait(streams,timeout=30,return_when=asyncio.FIRST_COMPLETED)
    except (OSError,TimeoutError,asyncio.IncompleteReadError,asyncio.LimitOverrunError):
        pass
    finally:
        for task in streams:
            task.cancel()
        await asyncio.gather(*streams,return_exceptions=True)
        if remote:
            remote.close()
        client.close()


async def serve(destination):
    server = await asyncio.start_server(lambda r,w:tunnel(r,w,destination),LISTENER,PORT,limit=2048)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(serve(upstream(sys.argv[1])))
