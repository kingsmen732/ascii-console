# import cv2
# import os
# import sys
# import time
# import threading
# from http.server import BaseHTTPRequestHandler, HTTPServer

# # ASCII_CHARS = "~*+=-:. "
# # ASCII_CHARS ="~`^,:;!><~+_-?][}{)(|\\/*<*>" # More detailed
# ASCII_CHARS = "@%#*+=-:. "  # More contrast
# WIDTH = 200  # Console width in characters

# latest_ascii_frame = ""
# frame_lock = threading.Lock()

# def frame_to_ascii(frame, width=WIDTH, threshold=25):
#     height, w = frame.shape
#     aspect_ratio = height / w
#     new_height = int(aspect_ratio * width * 0.55)
#     resized = cv2.resize(frame, (width, new_height))
#     ascii_frame = ""
#     for row in resized:
#         for pixel in row:
#             if pixel < threshold:
#                 ascii_frame += " "  # Black/dark pixel as space
#             else:
#                 # ascii_frame += ASCII_CHARS[pixel * len(ASCII_CHARS) // 256]
#                 ascii_frame += ASCII_CHARS[int(pixel) * len(ASCII_CHARS) // 256]

#         ascii_frame += "\n"
#     return ascii_frame

# def play_video_ascii(video_path):
#     global latest_ascii_frame
#     cap = cv2.VideoCapture(video_path)
#     if not cap.isOpened():
#         print("Error: Cannot open video.")
#         return

#     # Check for CUDA support
#     use_cuda = False
#     try:
#         _ = cv2.cuda.getCudaEnabledDeviceCount()
#         use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
#     except Exception:
#         use_cuda = False

#     fps = cap.get(cv2.CAP_PROP_FPS)
#     if fps is None or fps <= 0:
#         fps = 30 # Default to 30 FPS if not available
#     print(f"Video FPS: {fps}")
#     print(f"Using CUDA: {use_cuda}")
#     delay = 1.0 / fps

#     try:
#         while True:
#             ret, frame = cap.read()
#             if not ret:
#                 break
#             if use_cuda:
#                 gpu_frame = cv2.cuda_GpuMat()
#                 gpu_frame.upload(frame)
#                 gpu_gray = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2GRAY)
#                 gray = gpu_gray.download()
#             else:
#                 gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#             ascii_art = frame_to_ascii(gray)
#             with frame_lock:
#                 latest_ascii_frame = ascii_art
#             time.sleep(delay)
#     except KeyboardInterrupt:
#         pass
#     finally:
#         cap.release()

# class AsciiHandler(BaseHTTPRequestHandler):
#     def do_GET(self):
#         if self.path == "/":
#             self.send_response(200)
#             self.send_header("Content-type", "text/html")
#             self.end_headers()
#             html = """
#             <html>
#             <head>
#                 <title>ASCII Video Stream</title>
#                 <style>
#                     body { background: #222; color: #eee; font-family: monospace; }
#                     pre { font-size: 8px; line-height: 7px; }
#                 </style>
#                 <script>
#                     function fetchFrame() {
#                         fetch('/frame')
#                             .then(response => response.text())
#                             .then(data => {
#                                 document.getElementById('ascii').textContent = data;
#                             });
#                     }
#                     setInterval(fetchFrame, 80);
#                     window.onload = fetchFrame;
#                 </script>
#             </head>
#             <body>
#                 <pre id="ascii"></pre>
#             </body>
#             </html>
#             """
#             self.wfile.write(html.encode("utf-8"))
#         elif self.path == "/frame":
#             self.send_response(200)
#             self.send_header("Content-type", "text/plain")
#             self.end_headers()
#             with frame_lock:
#                 self.wfile.write(latest_ascii_frame.encode("utf-8"))
#         else:
#             self.send_error(404)

# def run_server(port=8080):
#     server_address = ('', port)
#     httpd = HTTPServer(server_address, AsciiHandler)
#     print(f"Serving ASCII video at http://localhost:{port}/")
#     httpd.serve_forever()

# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage: python webserver.py <video_path>")
#         sys.exit(1)
#     video_path = sys.argv[1]
#     if not os.path.isfile(video_path):
#         print(f"Error: File '{video_path}' does not exist.")
#         sys.exit(1)
#     t = threading.Thread(target=play_video_ascii, args=(video_path,), daemon=True)
#     t.start()
#     run_server()

import cv2
import os
import sys
import time
import threading
import numpy as np
from http.server import BaseHTTPRequestHandler, HTTPServer

# ASCII characters ordered from dark → light
ASCII_CHARS = "@%#*+=-:. "  
# ASCII_CHARS = "~*+=-:. "
WIDTH = 250  # Console width in characters

latest_ascii_frame = ""
frame_lock = threading.Lock()


def frame_to_ascii(frame, width=WIDTH):
    """Convert a grayscale frame to ASCII art using NumPy vectorization."""
    height, w = frame.shape
    aspect_ratio = height / w
    new_height = int(aspect_ratio * width * 0.55)

    # Resize on CPU (frame already grayscale from GPU/CPU pipeline)
    resized = cv2.resize(frame, (width, new_height))

    # Map grayscale values (0–255) → ASCII indices
    indices = (resized.astype(np.int32) * len(ASCII_CHARS) // 256)

    # Build ASCII image using NumPy char lookup
    ascii_chars = np.array(list(ASCII_CHARS))
    ascii_img = ascii_chars[indices]

    # Join rows into a single string
    return "\n".join("".join(row) for row in ascii_img)


def play_video_ascii(video_path):
    """Read video frames, process on GPU if available, and generate ASCII art."""
    global latest_ascii_frame
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Cannot open video.")
        return

    # Check for CUDA support
    try:
        use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
    except Exception:
        use_cuda = False

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps is None or fps <= 0:
        fps = 30  # Default to 30 FPS
    delay = 1.0 / fps

    print(f"Video FPS: {fps}")
    print(f"Using CUDA: {use_cuda}")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if use_cuda:
                # Upload to GPU
                gpu_frame = cv2.cuda_GpuMat()
                gpu_frame.upload(frame)

                # Convert to grayscale on GPU
                gpu_gray = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2GRAY)

                # Resize on GPU
                new_height = int((frame.shape[0] / frame.shape[1]) * WIDTH * 0.55)
                gpu_resized = cv2.cuda.resize(gpu_gray, (WIDTH, new_height))

                # Download back to CPU for ASCII conversion
                gray = gpu_resized.download()
            else:
                # CPU fallback
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Convert frame → ASCII art
            ascii_art = frame_to_ascii(gray)

            # Store latest frame for webserver
            with frame_lock:
                latest_ascii_frame = ascii_art

            time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()


class AsciiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = """
            <html>
            <head>
                <title>ASCII Video Stream</title>
                <style>
                    body { background: #222; color: #eee; font-family: monospace; }
                    pre { font-size: 8px; line-height: 7px; }
                </style>
                <script>
                    function fetchFrame() {
                        fetch('/frame')
                            .then(response => response.text())
                            .then(data => {
                                document.getElementById('ascii').textContent = data;
                            });
                    }
                    setInterval(fetchFrame, 80);
                    window.onload = fetchFrame;
                </script>
            </head>
            <body>
                <pre id="ascii"></pre>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/frame":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            with frame_lock:
                self.wfile.write(latest_ascii_frame.encode("utf-8"))
        else:
            self.send_error(404)


def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, AsciiHandler)
    print(f"Serving ASCII video at http://localhost:{port}/")
    httpd.serve_forever()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <video_path>")
        sys.exit(1)
    video_path = sys.argv[1]
    if not os.path.isfile(video_path):
        print(f"Error: File '{video_path}' does not exist.")
        sys.exit(1)

    t = threading.Thread(target=play_video_ascii, args=(video_path,), daemon=True)
    t.start()
    run_server()
