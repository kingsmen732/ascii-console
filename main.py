import cv2
import os
import sys
import time

ASCII_CHARS = "~*+=-:. "
# ASCII_CHARS ="~`^,:;!><~+_-?][}{)(|\\/*<*>" # More detailed
# ASCII_CHARS = "@%#*+=-:. "  # More contrast
WIDTH = 100  # Console width in characters

def frame_to_ascii(frame, width=WIDTH, threshold=25):
    height, w = frame.shape
    aspect_ratio = height / w
    new_height = int(aspect_ratio * width * 0.55)
    resized = cv2.resize(frame, (width, new_height))
    ascii_frame = ""
    for row in resized:
        for pixel in row:
            if pixel < threshold:
                ascii_frame += " "  # Black/dark pixel as space
            else:
                # ascii_frame += ASCII_CHARS[pixel * len(ASCII_CHARS) // 256]
                ascii_frame += ASCII_CHARS[int(pixel) * len(ASCII_CHARS) // 256]

        ascii_frame += "\n"
    return ascii_frame


def play_video_ascii(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Cannot open video.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps is None or fps <= 0:
        fps = 12  # Default to 30 FPS if not available
    print(f"Video FPS: {fps}")
    delay = 1.5 / fps

    try:
        last_time = time.time()
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            ascii_art = frame_to_ascii(gray)
            # Avoid clearing the console every frame for smoother output
            print('\033[H', end='')  # Move cursor to top (ANSI escape)
            print(ascii_art)
            elapsed = time.time() - last_time
            sleep_time = max(0, delay - elapsed)
            time.sleep(sleep_time)
            last_time = time.time()
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()




if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <video_path>")
        sys.exit(1)
    video_path = sys.argv[1]
    if not os.path.isfile(video_path):
        print(f"Error: File '{video_path}' does not exist.")
        sys.exit(1)
    play_video_ascii(video_path)