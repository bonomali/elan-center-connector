#!/usr/bin/env python3

import asyncio
import websockets

async def handle_mqtt(tcp_reader, tcp_writer):
    try:
        async with websockets.connect('ws://127.0.0.1:8000/mqtt', subprotocols=['mqtt']) as websocket:
            while True:
                from_tcp = asyncio.ensure_future( tcp_reader.read(1024) )
                from_ws = asyncio.ensure_future(websocket.recv())
                
                done, _pending = await asyncio.wait(
                                   [from_tcp, from_ws],
                                   return_when=asyncio.FIRST_COMPLETED)
                
                if from_tcp in done:
                    data = from_tcp.result()
                    if not data:
                        from_ws.cancel()
                        break
                    await websocket.send(data)
                else:
                    from_tcp.cancel()
            
                if from_ws in done:
                    if from_ws.exception() is not None:
                        from_tcp.cancel()
                        break
                    data = from_ws.result()
                    tcp_writer.write(data)
                    await tcp_writer.drain()
                else:
                    from_ws.cancel()
    except Exception as e:
        print(e)
    finally:
        tcp_writer.write_eof()

                
coro = asyncio.start_server(handle_mqtt, '127.0.0.1', 1884)
loop = asyncio.get_event_loop()
server = loop.run_until_complete(coro)

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
