# Changelog

## v1.1.0 (2026-04-14)

### Features

- **MQTT Print Client**: Home Assistant integration via MQTT
  - Subscribe to `paperang/print/text` for text printing
  - Subscribe to `paperang/print/image` for image printing
  - Subscribe to `paperang/print/qr` for QR code printing
  - JSON payload support with configurable parameters
  - Systemd service for auto-start

### Added

- `mqtt_print.py`: MQTT client for remote printing
- Systemd service configuration for mqtt-print.service

## v1.0.0 (2026-04-12)

### Features

- **Text Printing**: Print text with CJK (Chinese, Japanese, Korean) font support
  - Adjustable font size
  - Automatic line wrapping
  - Multi-line text support

- **Image Printing**: Print images with fine-tuned controls
  - Adjustable binarization threshold (0-255)
  - Brightness multiplier
  - Contrast multiplier
  - Automatic resize to 576 pixels width

- **QR Code Printing**: Generate and print QR codes
  - Configurable size (up to 576 pixels)
  - Centered on paper
  - Automatic version selection

- **Print Profiles**: Pre-configured settings for different content types
  - `portrait`: Optimized for portrait photos with glasses
  - `landscape`: Optimized for nature/landscape photos
  - `document`: Optimized for text documents
  - `high_contrast`: High contrast for bold images
  - `light`: Light printing for saving paper

- **Test Functions**
  - Pattern test: Test line/column/multi-packet transmission
  - Heat density test: Show different density levels

- **Status Reading**
  - Read printer status
  - Read battery level

### Technical Details

- **Protocol**: Paperang P2 USB protocol
  - Vendor ID: 0x4348
  - Product ID: 0x5584
  - Print width: 576 pixels (72 bytes/line)
  - Row-based bitmap packing
  - 14 lines per packet (1008 bytes)
  - Custom CRC32 with seed 0x35769521

### Requirements

- Python 3
- pyusb
- Pillow
- qrcode[pil] (optional, for QR code printing)

### Installation

```bash
pip3 install pyusb pillow qrcode[pil]
```

Or system-wide:
```bash
sudo apt-get install python3-usb python3-pil python3-qrcode
```

### Usage

```bash
# Print text
sudo python3 paperang_p2.py -t "Hello World"

# Print image with profile
sudo python3 paperang_p2.py -i photo.jpg -p portrait

# Print QR code
sudo python3 paperang_p2.py -q "https://example.com"

# List profiles
python3 paperang_p2.py --list-profiles

# Get status/battery
sudo python3 paperang_p2.py --status
sudo python3 paperang_p2.py --battery
```

### License

MIT License
