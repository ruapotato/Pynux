#!/usr/bin/env python3
"""
VTNext Renderer - Displays graphics from VTNext protocol over serial/stdin

Protocol: ESC ] vtn ; <command> ; <params> BEL

Usage:
    ./build.sh --run 2>&1 | python3 vtnext/renderer.py
    # or with QEMU:
    qemu-system-arm ... -serial stdio | python3 vtnext/renderer.py
"""

import sys
import re
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame not installed. Install with: pip install pygame", file=sys.stderr)

# Default screen size
WIDTH = 800
HEIGHT = 600

# Parse VTNext commands from input
class VTNextParser:
    def __init__(self):
        self.buffer = ""
        self.in_command = False
        self.commands = []

    def feed(self, data: str):
        """Feed data to parser, returns list of parsed commands."""
        self.buffer += data
        commands = []

        while True:
            # Look for ESC ] vtn ;
            start = self.buffer.find('\x1b]vtn;')
            if start == -1:
                # No command start, keep last few chars in case of split
                if len(self.buffer) > 10:
                    # Print non-command text
                    print(self.buffer[:-10], end='', flush=True)
                    self.buffer = self.buffer[-10:]
                break

            # Print text before command
            if start > 0:
                print(self.buffer[:start], end='', flush=True)

            # Find command end (BEL = 0x07)
            end = self.buffer.find('\x07', start)
            if end == -1:
                # No end yet, wait for more data
                self.buffer = self.buffer[start:]
                break

            # Extract command
            cmd_str = self.buffer[start+6:end]  # Skip 'ESC]vtn;'
            self.buffer = self.buffer[end+1:]

            # Parse command
            cmd = self.parse_command(cmd_str)
            if cmd:
                commands.append(cmd)

        return commands

    def parse_command(self, cmd_str: str):
        """Parse a VTNext command string into a command dict."""
        parts = cmd_str.split(';')
        if not parts:
            return None

        cmd_name = parts[0]
        params = parts[1:] if len(parts) > 1 else []

        return {'cmd': cmd_name, 'params': params}


class VTNextRenderer:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.screen = None
        self.font = None

        if PYGAME_AVAILABLE:
            pygame.init()
            self.screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption("Pynux VTNext")
            self.font = pygame.font.SysFont('monospace', 16)
            self.screen.fill((0, 0, 0))
            pygame.display.flip()

    def handle_command(self, cmd):
        """Handle a parsed VTNext command."""
        if not PYGAME_AVAILABLE:
            return

        name = cmd['cmd']
        params = cmd['params']

        try:
            if name == 'clear':
                if len(params) >= 4:
                    r, g, b, a = int(params[0]), int(params[1]), int(params[2]), int(params[3])
                    self.clear(r, g, b, a)
            elif name == 'rect':
                if len(params) >= 8:
                    x, y, w, h = int(params[0]), int(params[1]), int(params[2]), int(params[3])
                    r, g, b, a = int(params[4]), int(params[5]), int(params[6]), int(params[7])
                    self.rect(x, y, w, h, r, g, b, a)
            elif name == 'circle':
                if len(params) >= 7:
                    x, y, radius = int(params[0]), int(params[1]), int(params[2])
                    r, g, b, a = int(params[3]), int(params[4]), int(params[5]), int(params[6])
                    self.circle(x, y, radius, r, g, b, a)
            elif name == 'line':
                if len(params) >= 9:
                    x1, y1, x2, y2 = int(params[0]), int(params[1]), int(params[2]), int(params[3])
                    thickness = int(params[4])
                    r, g, b, a = int(params[5]), int(params[6]), int(params[7]), int(params[8])
                    self.line(x1, y1, x2, y2, thickness, r, g, b, a)
            elif name == 'text':
                # Format: x;y;z;rotation;scale;r;g;b;a;"text"
                if len(params) >= 10:
                    x, y = int(params[0]), int(params[1])
                    # z = params[2], rotation = params[3] (unused for now)
                    scale = int(params[4])
                    r, g, b, a = int(params[5]), int(params[6]), int(params[7]), int(params[8])
                    text = params[9].strip('"')
                    self.text(text, x, y, scale, r, g, b, a)
            elif name == 'print':
                if len(params) >= 3:
                    text = params[0]
                    x, y = int(params[1]), int(params[2])
                    self.text(text, x, y, 1, 255, 255, 255, 255)
            elif name == 'present':
                self.present()
            elif name == 'viewport':
                if len(params) >= 2:
                    w, h = int(params[0]), int(params[1])
                    self.resize(w, h)
        except (ValueError, IndexError) as e:
            print(f"VTNext: Error parsing {name}: {e}", file=sys.stderr)

    def clear(self, r, g, b, a):
        self.screen.fill((r, g, b))

    def rect(self, x, y, w, h, r, g, b, a):
        pygame.draw.rect(self.screen, (r, g, b), (x, y, w, h))

    def circle(self, cx, cy, radius, r, g, b, a):
        pygame.draw.circle(self.screen, (r, g, b), (cx, cy), radius)

    def line(self, x1, y1, x2, y2, thickness, r, g, b, a):
        pygame.draw.line(self.screen, (r, g, b), (x1, y1), (x2, y2), thickness)

    def text(self, text, x, y, scale, r, g, b, a):
        font = pygame.font.SysFont('monospace', 16 * scale)
        surface = font.render(text, True, (r, g, b))
        self.screen.blit(surface, (x, y))

    def present(self):
        pygame.display.flip()
        pygame.event.pump()  # Ensure display updates

    def resize(self, w, h):
        self.width = w
        self.height = h
        self.screen = pygame.display.set_mode((w, h))

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        return True


def main():
    parser = VTNextParser()
    renderer = VTNextRenderer(WIDTH, HEIGHT)

    print("VTNext Renderer - waiting for graphics commands...")
    print("(Reading from stdin, Ctrl+C to exit)")

    stdin_eof = False
    try:
        while True:
            # Check pygame events
            if PYGAME_AVAILABLE and not renderer.process_events():
                break

            # Read available input (non-blocking)
            import select
            if not stdin_eof and select.select([sys.stdin], [], [], 0.01)[0]:
                # Read multiple characters at once for efficiency
                data = sys.stdin.read(1024)
                if not data:
                    stdin_eof = True
                    print("Input complete. Close window to exit.", file=sys.stderr)
                    continue
                commands = parser.feed(data)
                for cmd in commands:
                    renderer.handle_command(cmd)
                # Process events after handling commands to update display
                if PYGAME_AVAILABLE:
                    renderer.process_events()

    except KeyboardInterrupt:
        print("\nExiting...")

    if PYGAME_AVAILABLE:
        pygame.quit()


if __name__ == '__main__':
    main()
