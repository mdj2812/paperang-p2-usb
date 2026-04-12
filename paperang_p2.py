#!/usr/bin/env python3
"""
Paperang P2 USB Printer Control Script
Based on https://github.com/hurui200320/java-paperang-p2-usb protocol
Supports: text printing, image printing, QR code printing, test patterns, heat density adjustment
Author: OpenClaw
"""

import usb.core
import usb.util
import struct
import zlib
import sys
import os
import argparse
import random
from PIL import Image, ImageDraw, ImageFont

# Paperang P2 USB IDs
VENDOR_ID = 0x4348
PRODUCT_ID = 0x5584
CRC_SEED = 0x35769521 & 0xffffffff

# Print width (from Java project: PAPERANG_P2_PRINT_BIT_PER_LINE = 576)
PRINT_WIDTH = 576  # pixels (72 bytes/line * 8)
LINE_BYTES = 72    # bytes per line
MAX_PACKET_DATA = 1023  # max data per packet


def crc32_paperang(data, seed=CRC_SEED):
    """
    Paperang-specific CRC32 calculation
    Uses seed = 0x35769521 (standard CRC32 uses 0x00000000)
    """
    crc = zlib.crc32(data, seed) & 0xffffffff
    # Convert to signed 32-bit integer
    if crc > 2147483647:
        crc = crc - 4294967296
    return crc


def pack_packet(cmd, data=b'', packet_remain=0):
    """
    Pack Paperang protocol packet
    Format: [0x02] [CMD:1B] [packetRemain:1B] [dataLength:2B LE] [DATA:0-1023B] [CRC32:4B LE] [0x03]
    
    Args:
        cmd: Command byte
        data: Data content
        packet_remain: Remaining packet count (0 means this is the last packet)
    """
    crc = crc32_paperang(data)
    packet = bytearray()
    packet.append(0x02)                           # Packet header
    packet.append(cmd & 0xFF)                     # Command (1 byte)
    packet.append(packet_remain & 0xFF)           # Remaining packets (1 byte)
    packet.extend(struct.pack('<H', len(data)))   # Data length (2 bytes, little-endian)
    packet.extend(data)                           # Data (0-1023 bytes)
    packet.extend(struct.pack('<i', crc))         # CRC32 (4 bytes, little-endian, signed)
    packet.append(0x03)                           # Packet footer
    return bytes(packet)


class PaperangP2:
    def __init__(self):
        self.dev = None
        self.ep_out = None
        self.ep_in = None
        
    def connect(self):
        """Connect to printer"""
        self.dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if self.dev is None:
            raise RuntimeError("Paperang P2 printer not found")
        
        # Detach kernel driver if active
        if self.dev.is_kernel_driver_active(0):
            self.dev.detach_kernel_driver(0)
        
        # Set configuration
        self.dev.set_configuration()
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]
        
        # Find endpoints
        self.ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        self.ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
        )
        
        return True
    
    def send(self, cmd, data=b''):
        """Send command"""
        packet = pack_packet(cmd, data)
        self.dev.write(self.ep_out.bEndpointAddress, packet)
        return True
    
    def send_multi_packet(self, cmd, data):
        """
        Send multi-packet data (for large data printing)
        Splits data according to Paperang protocol, max 1023 bytes per packet
        """
        total_len = len(data)
        offset = 0
        packet_idx = 0
        
        while offset < total_len:
            # Calculate remaining packets
            remaining = total_len - offset
            current_packet_data_len = min(MAX_PACKET_DATA, remaining)
            next_offset = offset + current_packet_data_len
            packets_remain = (total_len - next_offset + MAX_PACKET_DATA - 1) // MAX_PACKET_DATA
            
            chunk = data[offset:next_offset]
            packet = pack_packet(cmd, chunk, packets_remain)
            self.dev.write(self.ep_out.bEndpointAddress, packet)
            
            offset = next_offset
            packet_idx += 1
        
        return True
    
    def feed(self, lines=100):
        """Feed paper (command 0x1A)"""
        return self.send(0x1A, struct.pack('<H', lines))
    
    def set_heat_density(self, density=75):
        """
        Set heat density/print darkness (command 0x19)
        Range: 0-100 (0=lightest, 100=darkest)
        Default 75 is a good balance
        """
        if density < 0:
            density = 0
        if density > 100:
            density = 100
        return self.send(0x19, struct.pack('<H', density))
    
    def set_paper_type(self, paper_type=0):
        """Set paper type (0=normal, 1=continuous)"""
        return self.send(0x2C, bytes([paper_type]))
    
    def print_test_page(self):
        """Print test page"""
        return self.send(0x1B)
    
    def get_status(self):
        """Get printer status"""
        self.send(0x0C)
        try:
            resp = self.dev.read(self.ep_in.bEndpointAddress, 64, timeout=1000)
            return resp
        except:
            return None
    
    def get_battery(self):
        """Get battery level"""
        self.send(0x10)
        try:
            resp = self.dev.read(self.ep_in.bEndpointAddress, 64, timeout=1000)
            return resp
        except:
            return None
    
    def print_bitmap(self, bitmap_data, width_bytes=72):
        """Print bitmap data (row-based packet splitting, based on Java project)"""
        # Lines per packet: 1023 / 72 = 14 lines
        lines_per_packet = MAX_PACKET_DATA // width_bytes  # 14
        
        total_bytes = len(bitmap_data)
        total_lines = total_bytes // width_bytes
        
        # Calculate total packets
        total_packets = (total_lines + lines_per_packet - 1) // lines_per_packet
        
        offset = 0
        line_offset = 0
        packet_idx = 0
        
        while offset < total_bytes:
            # Calculate lines for current packet
            remaining_lines = total_lines - line_offset
            current_lines = min(lines_per_packet, remaining_lines)
            current_bytes = current_lines * width_bytes
            
            # Calculate remaining packets (after this packet)
            packet_idx += 1
            remaining_packets = total_packets - packet_idx
            
            chunk = bitmap_data[offset:offset + current_bytes]
            packet = pack_packet(0x00, chunk, remaining_packets)
            self.dev.write(self.ep_out.bEndpointAddress, packet)
            
            offset += current_bytes
            line_offset += current_lines
        
        return True
    
    def print_image(self, image_path, heat_density=75, feed_before=50, feed_after=300):
        """
        Print image file
        
        Args:
            image_path: Path to image file
            heat_density: Heat density 0-100 (default 75)
            feed_before: Paper feed before printing (default 50)
            feed_after: Paper feed after printing (default 300)
        """
        # Open image
        img = Image.open(image_path)
        
        # Resize to 576 pixels width
        if img.width != PRINT_WIDTH:
            ratio = PRINT_WIDTH / img.width
            new_height = int(img.height * ratio)
            img = img.resize((PRINT_WIDTH, new_height), Image.LANCZOS)
        
        # Convert to grayscale then binarize (if not already 1-bit)
        if img.mode != '1':
            img = img.convert('L')
            img = img.point(lambda x: 0 if x < 128 else 255, '1')
        
        # Convert to bitmap data (based on Java project's toByteArrays())
        # Row-based packing: 72 bytes per line, each byte's 8 bits represent 8 horizontal pixels
        # bitPos = 7 - (x % 8), i.e., MSB on left
        width_bytes = PRINT_WIDTH // 8  # 72
        height = img.height
        
        # Pack data by row
        data = bytearray()
        for y in range(height):
            row = bytearray(width_bytes)
            for x in range(PRINT_WIDTH):
                if img.getpixel((x, y)) == 0:  # Black pixel
                    byte_pos = x // 8
                    bit_pos = 7 - (x % 8)  # MSB on left
                    row[byte_pos] |= (1 << bit_pos)
            data.extend(row)
        
        # Print flow (based on Java project)
        self.set_paper_type(0)           # Set normal paper
        self.set_heat_density(heat_density)  # Set heat density
        self.feed(feed_before)           # Feed before printing
        self.print_bitmap(bytes(data), width_bytes)  # Send print data
        self.feed(feed_after)            # Feed after printing
        return True
    
    def print_text(self, text, font_size=24, heat_density=75):
        """Print text"""
        # Try to load fonts (prioritize CJK-supporting fonts)
        font_paths = [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
        font = None
        for fp in font_paths:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, font_size)
                break
        if font is None:
            font = ImageFont.load_default()
        
        # Calculate dimensions
        lines = text.split('\n')
        max_width = 0
        total_height = 0
        line_heights = []
        
        for line in lines:
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0] if bbox else len(line) * font_size // 2
            # Use bbox[3] as height (includes space below baseline)
            h = bbox[3] if bbox else font_size
            max_width = max(max_width, w)
            line_heights.append(h + 4)
            total_height += h + 4
        
        # Create image (width must be 576, height must be multiple of 8)
        img_width = PRINT_WIDTH  # 576
        img_height = ((total_height + 20 + 7) // 8) * 8  # Round up to multiple of 8
        img = Image.new('1', (img_width, img_height), 1)
        draw = ImageDraw.Draw(img)
        
        # Draw text
        y = 10
        for i, line in enumerate(lines):
            draw.text((10, y), line, font=font, fill=0)
            y += line_heights[i]
        
        # Save temp file and print
        tmp_path = '/tmp/paperang_text.png'
        img.save(tmp_path)
        return self.print_image(tmp_path, heat_density=heat_density)
    
    def print_qr(self, content, box_size=10, heat_density=75):
        """Print QR code"""
        try:
            import qrcode
        except ImportError:
            print("Please install qrcode: pip3 install qrcode[pil]")
            return False
        
        qr = qrcode.QRCode(version=1, box_size=box_size, border=2)
        qr.add_data(content)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Center the QR code
        qr_size = min(img.width, PRINT_WIDTH - 40)
        img = img.resize((qr_size, qr_size), Image.NEAREST)
        
        canvas = Image.new('1', (PRINT_WIDTH, qr_size + 20), 1)
        offset_x = (PRINT_WIDTH - qr_size) // 2
        canvas.paste(img, (offset_x, 10))
        
        tmp_path = '/tmp/paperang_qr.png'
        canvas.save(tmp_path)
        return self.print_image(tmp_path, heat_density=heat_density)
    
    def print_pattern_test(self):
        """
        Print pattern test (based on UsbPatternTest.kt)
        Tests: line length, dots per line, dots per column, multi-packet transmission
        """
        width_bytes = LINE_BYTES  # 72 bytes = 576 dots
        
        # Create test pattern data
        data = bytearray()
        
        # 1. Test line length - print columns every 8 bytes
        # Print 8 columns, each 8 bytes wide
        for _ in range(50):  # 50 rows
            row = bytearray(width_bytes)
            for col in range(8):  # 8 columns
                start_byte = col * 9  # 9 bytes per column (72/8=9)
                for b in range(9):
                    row[start_byte + b] = 0xFF
            data.extend(row)
        
        # 2. Test dots per line - alternating pattern 10101010
        for _ in range(50):
            row = bytearray(width_bytes)
            for b in range(width_bytes):
                row[b] = 0xAA  # 10101010
            data.extend(row)
        
        # 3. Test dots per column - vertical lines
        for _ in range(50):
            row = bytearray(width_bytes)
            for b in range(width_bytes):
                row[b] = 0x81  # 10000001 - vertical lines on both sides
            data.extend(row)
        
        # 4. Random data test for multi-packet transmission
        for _ in range(100):
            row = bytearray(width_bytes)
            for b in range(width_bytes):
                row[b] = random.randint(0, 255)
            data.extend(row)
        
        # Print flow
        self.set_paper_type(0)
        self.set_heat_density(75)
        self.feed(50)
        self.print_bitmap(bytes(data), width_bytes)
        self.feed(300)
        return True
    
    def print_heat_density_test(self):
        """
        Print heat density test (based on UsbHeatDensityTest.kt)
        Shows printing effect at different heat densities
        """
        width_bytes = LINE_BYTES
        
        densities = [0, 25, 50, 75, 100]
        
        for density in densities:
            # Set heat density
            self.set_heat_density(density)
            
            # Print density marker bar
            data = bytearray()
            
            # Top blank
            for _ in range(20):
                data.extend(bytearray(width_bytes))
            
            # Solid block
            for _ in range(30):
                row = bytearray(width_bytes)
                for b in range(width_bytes):
                    row[b] = 0xFF
                data.extend(row)
            
            # Bottom blank
            for _ in range(20):
                data.extend(bytearray(width_bytes))
            
            self.print_bitmap(bytes(data), width_bytes)
            self.feed(50)
        
        # Restore default density
        self.set_heat_density(75)
        self.feed(300)
        return True


def main():
    parser = argparse.ArgumentParser(description='Paperang P2 Printer Control')
    parser.add_argument('-t', '--text', help='Print text')
    parser.add_argument('-i', '--image', help='Print image')
    parser.add_argument('-q', '--qr', help='Print QR code')
    parser.add_argument('-f', '--font-size', type=int, default=24, help='Font size')
    parser.add_argument('-d', '--density', type=int, default=75, help='Heat density 0-100 (default 75)')
    parser.add_argument('--test', action='store_true', help='Print test page')
    parser.add_argument('--pattern-test', action='store_true', help='Print pattern test (test line/column/multi-packet)')
    parser.add_argument('--density-test', action='store_true', help='Print heat density test')
    parser.add_argument('--status', action='store_true', help='Get printer status')
    parser.add_argument('--battery', action='store_true', help='Get battery level')
    
    args = parser.parse_args()
    
    printer = PaperangP2()
    
    try:
        printer.connect()
        
        if args.test:
            printer.print_test_page()
        elif args.pattern_test:
            printer.print_pattern_test()
        elif args.density_test:
            printer.print_heat_density_test()
        elif args.status:
            status = printer.get_status()
            print(f"Status: {status}")
        elif args.battery:
            battery = printer.get_battery()
            print(f"Battery: {battery}")
        elif args.text:
            printer.print_text(args.text, font_size=args.font_size, heat_density=args.density)
        elif args.image:
            printer.print_image(args.image, heat_density=args.density)
        elif args.qr:
            printer.print_qr(args.qr, heat_density=args.density)
        else:
            # Default test text
            test_text = """Paperang P2 Test Print
==================
Printer working!

Time: """ + os.popen('date "+%Y-%m-%d %H:%M:%S"').read().strip()
            printer.print_text(test_text, heat_density=args.density)
        
        print("Print complete!")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
