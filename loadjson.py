#!/usr/bin/env python

import asyncio
import websockets
import json
import sys

async def test_client():
    try:
        with open(image_file, 'r') as file:
            data = json.load(file)
        print(json.dumps(data, indent=4))
    except FileNotFoundError:
        print(f"Error: The file '{image_file}' was not found.")
        quit()
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{image_file}'. Check file format.")
        quit()


    try:
        uri = "ws://ledarray1:8765"
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps(data))
            print(f"Sent: {data}")
    except:
        print(f"Error connecting to websocket server on {uri}")

# Run the client
if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Require a json file argument")
    else:
        image_file = sys.argv[1]

    asyncio.run(test_client())

