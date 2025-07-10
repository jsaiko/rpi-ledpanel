#!/usr/bin/env python

import asyncio
import websockets
import json
import signal
import base64
import io
from rgbmatrix import graphics, RGBMatrix, RGBMatrixOptions
from PIL import Image

shutdown_event = asyncio.Event()
config_updated = True
configuration = {
    "data": {
        "scenes": [
            {
                "type": "string",
                "value": "Welcome!",
                "color": {"r": 255, "g": 255, "b": 0},
                "effect": "scroll"
            },        
        ]
    },
    "options": {
        "action": "loop",
        "scrollspeed": 1,
        "scrolldelay": 0.05,
    }
}

# Handle new WebSocket connections
async def handle_connection(websocket):
    global configuration
    global config_updated

    print(f"New connection from: {websocket.remote_address}")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                print("Received JSON:", data)
                configuration = data

                # verify data
                if "scrolldelay" not in configuration["options"]:
                    if "scrollspeed" not in configuration["options"]:
                        configuration["options"]["scrollspeed"] = 1
                    configuration["options"]["scrolldelay"] = 0.05 / configuration["options"]["scrollspeed"]

                for scene in configuration["data"]["scenes"][:]:
                    if "type" not in scene or "value" not in scene:
                        configuration["data"]["scenes"].remove(scene)
                        print(f"Deleting scene {scene} due to missing required keys!")
                    if "color" not in scene:
                        scene["color"] = {"r":255,"g":255,"b":0}
                    if "r" not in scene["color"]:
                        scene["color"]["r"] = 0
                    if "g" not in scene["color"]:
                        scene["color"]["g"] = 0
                    if "b" not in scene["color"]:
                        scene["color"]["b"] = 0
                    if "effect" not in scene:
                        scene["effect"] = "none"
                    if "display" not in scene:
                        scene["display"] = "center"
                    if "time" not in scene:
                        if scene["effect"] == "scroll":
                            scene["time"] = 0 # default of zero
                        else:
                            scene["time"] = 5 # default of 5s

                config_updated = True
            except json.JSONDecodeError:
                print("Invalid JSON received:", message)
    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")

# Signal handler
def signal_handler():
    print("Shutdown signal received.")
    shutdown_event.set()

# Render
async def render_task():
    global configuration
    global config_updated

    # Set options
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 2
    options.parallel = 1
    options.row_address_type = 0
    options.multiplexing = 0
    #options.pwm_bits = self.args.led_pwm_bits
    #options.brightness = self.args.led_brightness
    #options.pwm_lsb_nanoseconds = self.args.led_pwm_lsb_nanoseconds
    #options.led_rgb_sequence = self.args.led_rgb_sequence
    #options.pixel_mapper_config = self.args.led_pixel_mapper
    #options.panel_type = self.args.led_panel_type    

    # Init matrix
    matrix = RGBMatrix(options = options)

    # Main render loop
    while not shutdown_event.is_set():
        await asyncio.sleep(0.01)
        config_updated = False

        # Iter each scene
        for scene in configuration["data"]["scenes"]:
            # Sanity checks
            if config_updated:
                break
            
            match scene["type"]:
                case "string":
                    # Init canvas
                    offscreen_canvas = matrix.CreateFrameCanvas()
                    font = graphics.Font()
                    font.LoadFont("./fonts/spleen-16x32.bdf")
                    textColor = graphics.Color(scene["color"]["r"], scene["color"]["g"], scene["color"]["b"])
                    text = scene["value"]
                    width = offscreen_canvas.width
                    length = graphics.DrawText(offscreen_canvas, font, 0, 25, textColor, text)

                    # Calculate starting position
                    if scene["effect"] == "scroll":
                        pos = width
                    else:
                        match scene["display"]:
                            case "left":
                                pos = 0
                            case "right":
                                pos = (width - length)
                            case "center":
                                pos = (width - length) / 2

                    # Render scene
                    while not shutdown_event.is_set():
                        if config_updated:
                            break
                        offscreen_canvas.Clear()
                        length = graphics.DrawText(offscreen_canvas, font, pos, 25, textColor, text)
                        offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)

                        if scene["effect"] == "scroll":
                            pos -= 1
                            if pos + length < 0:
                                break
                            if "time" in scene:
                                if ((width - length) / 2) == pos:
                                    await asyncio.sleep(scene["time"])  # Non-blocking delay
                            await asyncio.sleep(configuration["options"]["scrolldelay"])  # Non-blocking delay
                        else:
                            match scene["display"]:
                                case "center" | "left" | "right":
                                    await asyncio.sleep(scene["time"])  # Non-blocking delay
                                    break
                case "image":
                    offscreen_canvas = matrix.CreateFrameCanvas()
                    base64_img = configuration["data"]["images"][scene["value"]]

                    # Remove the data URL prefix if present
                    if base64_img.startswith("data:"):
                        base64_img = base64_img.split(",")[1]

                    # Decode the base64 string
                    img_data = base64.b64decode(base64_img)

                    # Load image using BytesIO
                    image = Image.open(io.BytesIO(img_data))
                    width, height = image.size
                    pos_x = (offscreen_canvas.width - width) / 2

                    offscreen_canvas.SetImage(image, pos_x)
                    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
                    await asyncio.sleep(scene["time"])
                case _:
                    continue

# Main server function
async def main():
    async with websockets.serve(handle_connection, "0.0.0.0", 8765):
        print("WebSocket server listening on ws://0.0.0.0:8765")

        # Run the render task in parallel
        render = asyncio.create_task(render_task())

        # Wait for shutdown
        await shutdown_event.wait()

        # Cancel the render task gracefully
        render.cancel()
        try:
            await render
        except asyncio.CancelledError:
            print("Render task cancelled.")

        print("Shutting down server...")

# Entry point
if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        print("Server stopped.")
        loop.close()
