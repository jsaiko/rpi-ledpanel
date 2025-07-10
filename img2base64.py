#!/usr/bin/env python

import sys
import base64
import io
from PIL import Image

if len(sys.argv) < 2:
    sys.exit("Require a gif argument")
else:
    image_file = sys.argv[1]

gif = Image.open(image_file)

try:
    num_frames = gif.n_frames
except Exception:
    sys.exit("provided image is not a gif")

print("Processing gif, this may take a moment depending on the size of the gif...")
for frame_index in range(0, num_frames):
    gif.seek(frame_index)
    # must copy the frame out of the gif, since thumbnail() modifies the image in-place
    frame = gif.copy()
    RGB = frame.convert("RGB")

    # Convert image to bytes using BytesIO
    buffered = io.BytesIO()
    RGB.save(buffered, format="PNG")  # Change format if needed (e.g., "PNG")

    # Encode the image bytes to base64
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

    # Optional: Add prefix for embedding in HTML or CSS
    base64_img = f"data:image/png;base64,{img_str}"

    print(f"frame {frame_index}:")
    print(base64_img)







# Close the gif file to save memory now that we have copied out all of the frames
gif.close()