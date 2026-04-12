---
name: paperang-p2
description: Control Paperang P2 thermal printer via USB on Linux. Use when user wants to print text, images, or QR codes using a Paperang P2 printer connected via USB.
---

# Paperang P2 Printer Control

基于 [hurui200320/java-paperang-p2-usb](https://github.com/hurui200320/java-paperang-p2-usb) 协议实现的 Python 版本。

Control Paperang P2 thermal printer via USB on Linux systems.

## Requirements

- Paperang P2 printer connected via USB
- Python 3 with PIL/Pillow and pyusb
- sudo access for USB device access

## Installation

```bash
# Install dependencies
pip3 install --break-system-packages pyusb pillow qrcode[pil]

# Or system-wide
sudo apt-get install python3-usb python3-pil python3-qrcode
```

## Usage

### Command Line

```bash
# Print test page
echo <sudo_password> | sudo -S python3 scripts/paperang_p2.py --test

# Print pattern test (test line/column/multi-packet)
echo <sudo_password> | sudo -S python3 scripts/paperang_p2.py --pattern-test

# Print heat density test (show different density levels)
echo <sudo_password> | sudo -S python3 scripts/paperang_p2.py --density-test

# Print text
echo <sudo_password> | sudo -S python3 scripts/paperang_p2.py -t "Hello World"

# Print with custom heat density (0-100, default 75)
echo <sudo_password> | sudo -S python3 scripts/paperang_p2.py -t "Dark text" -d 100

# Print image
echo <sudo_password> | sudo -S python3 scripts/paperang_p2.py -i /path/to/image.png

# Print QR code
echo <sudo_password> | sudo -S python3 scripts/paperang_p2.py -q "https://example.com"

# Get status/battery
echo <sudo_password> | sudo -S python3 scripts/paperang_p2.py --status
echo <sudo_password> | sudo -S python3 scripts/paperang_p2.py --battery
```

### Python API

```python
from paperang_p2 import PaperangP2

printer = PaperangP2()
printer.connect()

# Print text with heat density
printer.print_text("Hello World", font_size=24, heat_density=75)

# Print image with heat density
printer.print_image("/path/to/image.png", heat_density=75)

# Print QR code
printer.print_qr("https://example.com", heat_density=75)

# Print test patterns
printer.print_pattern_test()      # Test line/column/multi-packet
printer.print_heat_density_test() # Show different density levels

# Manual control
printer.set_heat_density(75)  # 0-100
printer.feed(100)             # Feed paper
printer.set_paper_type(0)     # 0=normal, 1=continuous
```

## Protocol Details

Based on [java-paperang-p2-usb](https://github.com/hurui200320/java-paperang-p2-usb):

- Vendor ID: 0x4348
- Product ID: 0x5584
- Print width: 384 pixels (48 bytes/line)

### Packet Format

```
[0x02] [CMD:1B] [packetRemain:1B] [dataLength:2B LE] [DATA:0-1023B] [CRC32:4B LE] [0x03]
```

### Key Commands

| Command | Description |
|---------|-------------|
| 0x00 | Print bitmap data |
| 0x0C | Get status |
| 0x10 | Get battery level |
| 0x19 | Set heat density (0-100) |
| 0x1A | Feed paper |
| 0x1B | Print test page |
| 0x2C | Set paper type |

### CRC32

Uses custom seed `0x35769521` (standard CRC32 uses `0x00000000`).

## Troubleshooting

1. **Permission denied**: Ensure sudo access or add udev rules
2. **Device not found**: Check USB connection with `lsusb | grep 4348`
3. **Print too light**: Increase heat density with `-d 100`
4. **Print too dark**: Decrease heat density with `-d 50`
5. **No response**: Verify printer is powered on and has paper

## References

- [java-paperang-p2-usb](https://github.com/hurui200320/java-paperang-p2-usb) - Java implementation
- [python-paperang](https://github.com/tinyprinter/python-paperang) - Python Bluetooth version
- [Paperang protocol blog](https://www.ihcblog.com/miaomiaoji/) - Chinese blog post

## Script Location

The main script is at `scripts/paperang_p2.py`.
