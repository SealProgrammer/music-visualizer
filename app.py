#!/usr/bin/python3
import os
import struct
import subprocess
import pygame
import pygame.gfxdraw
import math
import fcntl
import time

pygame.font.init()

font = pygame.font.Font('./AirbeatFont.ttf', 30)

song_name = ""
album_name = ""
artist_name = ""

def update_data():
    command = ['playerctl', 'metadata', '--format', '("{{ title }}","{{ album }}","{{ artist }}")']

    # Run the command and capture the output
    result = subprocess.run(command, capture_output=True, text=True)

    # Print the output
    global song_name,album_name,artist_name
    try:
        song_name,album_name,artist_name = eval(result.stdout.strip())
    except SyntaxError as e: # no song is playing
        song_name,album_name,artist_name="","",""
update_data()

BARS_NUMBER = 64
OUTPUT_BIT_FORMAT = "16bit"
RAW_TARGET = "/dev/stdout"

bytetype, bytesize, bytenorm = ("H", 2, 65535) if OUTPUT_BIT_FORMAT == "16bit" else ("B", 1, 255)

def interpolate_color(colors, y_value):
    # Ensure y_value is between 0 and 1
    y_value = max(0, min(y_value, 1))
    
    # Get the number of colors
    num_colors = len(colors)
    
    # If there's only one color, return it
    if num_colors == 1:
        return colors[0]
    
    # Determine which two colors to interpolate between
    segment = y_value * (num_colors - 1)
    lower_index = int(segment)
    upper_index = min(lower_index + 1, num_colors - 1)
    
    # Calculate the interpolation factor
    factor = segment - lower_index
    
    # Get the two colors to interpolate between
    color1 = colors[lower_index]
    color2 = colors[upper_index]
    
    # Interpolate between color1 and color2
    r = int(color1[0] * (1 - factor) + color2[0] * factor)
    g = int(color1[1] * (1 - factor) + color2[1] * factor)
    b = int(color1[2] * (1 - factor) + color2[2] * factor)
    
    return (r, g, b)

colors = [
    (148, 226, 213),
    (137, 220, 235),
    (116, 199, 236),
    (137, 180, 250),
    (203, 166, 247),
    (245, 194, 231),
    (235, 160, 172),
    (243, 139, 168)
]

def set_nonblocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def run():
    process = subprocess.Popen(["cava", "-p", os.path.abspath("./cava_raw.cfg")], stdout=subprocess.PIPE)
    chunk = bytesize * BARS_NUMBER
    fmt = bytetype * BARS_NUMBER
    last_checked_time = time.time()

    pygame.init()
    screen = pygame.display.set_mode([1280, 720], pygame.RESIZABLE)

    if RAW_TARGET != "/dev/stdout":
        if not os.path.exists(RAW_TARGET):
            os.mkfifo(RAW_TARGET)
        source = open(RAW_TARGET, "rb", os.O_NONBLOCK)
    else:
        source = process.stdout
        # Set the source to non-blocking mode
        fd = source.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    subprocess.run(["playerctl", "play-pause"])
                if event.key == pygame.K_LEFT:
                    subprocess.run(["playerctl", "previous"])
                    update_data()
                if event.key == pygame.K_RIGHT:
                    subprocess.run(["playerctl", "next"])
                    update_data()
        
        latest_data = b''
        
        while True:
            try:
                data = source.read(chunk)
                if not data:
                    break
                latest_data = data  # Keep only the latest data
            except BlockingIOError:
                break
        
        if len(latest_data) < chunk:
            continue
        
        sample = [i / bytenorm for i in struct.unpack(fmt, latest_data)]

        screen.fill("#191724")
        
        w,h = screen.get_size()
        wrat, hrat = (w / BARS_NUMBER), (h / BARS_NUMBER)
        for y in range(0,h,h // 150):
            pygame.gfxdraw.box(screen, pygame.Rect(0, y, w, y + 2), pygame.color.Color(interpolate_color(colors, 1 - y / h)))

        for x, rh in enumerate(sample):
            height = -(rh * h) + (h - hrat)
            #for y in range(math.floor(height), h):
                # min(int(max(0, (y*255) / h)))
            #    pygame.gfxdraw.box(screen, pygame.Rect(x * wrat, 0, wrat - (wrat / 5), y), pygame.Color("#191724"))
            pygame.gfxdraw.box(screen, pygame.Rect(x * wrat + math.floor(wrat / 5), 0, math.ceil(wrat - (wrat / 5)) + 1, height), pygame.Color("#191724"))
            pygame.gfxdraw.box(screen, pygame.Rect(x * wrat, 0, wrat / 5, h), pygame.Color("#191724"))
        pygame.gfxdraw.box(screen, pygame.Rect(w - (wrat / 5), 0, (wrat / 5), h), pygame.Color("#191724"))

        if time.time() > last_checked_time + 5:
            last_checked_time = time.time()
            update_data()

        text_surface = font.render(song_name, True, (255, 255, 255))
        screen.blit(text_surface, (20, 20))
        text_surface = font.render(album_name, True, (255, 255, 255))
        screen.blit(text_surface, (20, 70))
        text_surface = font.render(artist_name, True, (255, 255, 255))
        screen.blit(text_surface, (20, 120))

        # print(time.time())
        pygame.display.flip()

if __name__ == "__main__":
    run()