#!/usr/bin/env python3
"""
VTNext Renderer - Displays graphics from VTNext protocol over serial/stdin

Protocol: ESC ] vtn ; <command> ; <params> BEL

Usage:
    ./boot_vm.sh                    # Recommended - handles bidirectional I/O
    # or manual:
    ./build.sh --run 2>&1 | python3 vtnext/renderer.py
"""

import sys
import os
import argparse
import select
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
            elif name == 'textline':
                # Format: x;y;r;g;b;"text"
                if len(params) >= 6:
                    x, y = int(params[0]), int(params[1])
                    r, g, b = int(params[2]), int(params[3]), int(params[4])
                    text = params[5].strip('"')
                    self.text(text, x, y, 1, r, g, b, 255)
            elif name == 'fillrect':
                # Format: x;y;w;h;r;g;b
                if len(params) >= 7:
                    x, y, w, h = int(params[0]), int(params[1]), int(params[2]), int(params[3])
                    r, g, b = int(params[4]), int(params[5]), int(params[6])
                    self.rect(x, y, w, h, r, g, b, 255)
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
        """Process pygame events, returns (running, keys_pressed)."""
        keys = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False, keys
            elif event.type == pygame.KEYDOWN:
                # Convert pygame key to character
                char = self.key_to_char(event)
                if char:
                    keys.append(char)
        return True, keys

    def key_to_char(self, event):
        """Convert pygame key event to character for UART."""
        key = event.key
        mods = event.mod

        # Regular printable characters first (most common case)
        # Check unicode before special keys to avoid conflicts
        if event.unicode and len(event.unicode) == 1:
            c = event.unicode
            # Only return if it's a normal printable ASCII character
            if 32 <= ord(c) <= 126:
                return c

        # Handle special keys
        if key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            return '\r'
        elif key == pygame.K_BACKSPACE:
            return '\x7f'  # DEL character
        elif key == pygame.K_DELETE:
            return '\x7f'
        elif key == pygame.K_ESCAPE:
            return '\x1b'
        elif key == pygame.K_TAB:
            return '\t'

        # Ctrl combinations (only when Ctrl is actually held)
        ctrl_only = (mods & pygame.KMOD_CTRL) and not (mods & (pygame.KMOD_ALT | pygame.KMOD_META))
        if ctrl_only:
            if key == pygame.K_c:
                return '\x03'  # Ctrl+C (interrupt)
            elif key == pygame.K_d:
                return '\x04'  # Ctrl+D (EOF)
            elif key == pygame.K_l:
                return '\x0c'  # Ctrl+L (clear)

        return None


def main():
    arg_parser = argparse.ArgumentParser(description='VTNext Renderer')
    arg_parser.add_argument('--fifo-in', help='FIFO to read graphics commands from')
    arg_parser.add_argument('--fifo-out', help='FIFO to write keyboard input to')
    args = arg_parser.parse_args()

    parser = VTNextParser()
    renderer = VTNextRenderer(WIDTH, HEIGHT)

    # Set up input/output streams
    if args.fifo_in:
        print(f"Opening FIFO for input: {args.fifo_in}", file=sys.stderr)
        input_fd = os.open(args.fifo_in, os.O_RDONLY | os.O_NONBLOCK)
        input_file = os.fdopen(input_fd, 'rb')
    else:
        input_file = sys.stdin.buffer if hasattr(sys.stdin, 'buffer') else sys.stdin

    output_file = None
    if args.fifo_out:
        print(f"Opening FIFO for output: {args.fifo_out}", file=sys.stderr)
        output_fd = os.open(args.fifo_out, os.O_WRONLY)
        output_file = os.fdopen(output_fd, 'wb', buffering=0)

    print("VTNext Renderer - waiting for graphics commands...", file=sys.stderr)
    if output_file:
        print("Keyboard input enabled", file=sys.stderr)

    input_eof = False
    try:
        while True:
            # Check pygame events and get key presses
            if PYGAME_AVAILABLE:
                running, keys = renderer.process_events()
                if not running:
                    break

                # Send key presses to output
                if output_file and keys:
                    for key in keys:
                        try:
                            output_file.write(key.encode('latin-1'))
                            output_file.flush()
                        except (BrokenPipeError, OSError):
                            pass

            # Read available input (non-blocking)
            try:
                if hasattr(input_file, 'fileno'):
                    fd = input_file.fileno()
                    if not input_eof and select.select([fd], [], [], 0.01)[0]:
                        data = input_file.read(4096)
                        if not data:
                            input_eof = True
                            print("Input complete. Close window to exit.", file=sys.stderr)
                            continue
                        # Decode bytes to string
                        if isinstance(data, bytes):
                            data = data.decode('latin-1', errors='replace')
                        commands = parser.feed(data)
                        for cmd in commands:
                            renderer.handle_command(cmd)
            except (ValueError, OSError):
                # File closed
                input_eof = True

    except KeyboardInterrupt:
        print("\nExiting...", file=sys.stderr)

    if PYGAME_AVAILABLE:
        pygame.quit()

    # Clean up
    if args.fifo_in and input_file:
        input_file.close()
    if output_file:
        output_file.close()


if __name__ == '__main__':
    main()
