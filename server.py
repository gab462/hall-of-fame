import asyncio
import websockets.asyncio as ws
import config
import message


clients: dict[bytes, ws.server.ServerConnection] = {}


async def handler(conn: ws.server.ServerConnection):
    from_id = conn.id.bytes

    try:
        buf = await conn.recv()
        assert isinstance(buf, bytes)

        msg = message.deserialize(buf)

        assert isinstance(msg, message.Hello)

        welcome = message.Welcome(from_id)
        await conn.send(message.serialize(welcome))

        for client_id, client in clients.items():
            await client.send(message.serialize(welcome))

        clients[from_id] = conn
    except Exception as e:
        print(f"Client failed to authenticate: {e}")
        await conn.close()
        return

    while True:
        try:
            buf = await conn.recv()
            assert isinstance(buf, bytes)
            msg = message.deserialize(buf)

            if isinstance(msg, message.Sync):  # This message has a set destination
                await clients[msg.to_id].send(message.serialize(msg))
            else:
                for client_id, client in clients.items():
                    if client_id == from_id:
                        continue

                    await client.send(message.serialize(msg))
        except (ws.connection.ConnectionClosed, ws.connection.ConnectionClosedOK):
            del clients[from_id]
            msg = message.Left(from_id)
            for client in clients.values():
                await client.send(message.serialize(msg))
            return
        except Exception as e:
            print(f"Error processing message: {e}")
            await conn.close()
            del clients[from_id]
            msg = message.Left(from_id)
            for client in clients.values():
                await client.send(message.serialize(msg))
            return


async def main():
    async with ws.server.serve(handler, config.ip, config.port) as server:
        print(f"Listening on {config.ip}:{config.port}")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
