# Paperang P2 USB Printer

Control Paperang P2 thermal printer via USB on Linux systems, with Home Assistant integration via MQTT.

Core logic powered by [paperang-p2-lib](https://github.com/mdj2812/paperang-p2-lib).

Based on [hurui200320/java-paperang-p2-usb](https://github.com/hurui200320/java-paperang-p2-usb) protocol implementation.

## Features

- **Text Printing** - CJK font support (Chinese, Japanese, Korean) with adjustable size
- **Image Printing** - Adjustable threshold, brightness, and contrast
- **QR Code Printing** - Auto-sized to fill paper width
- **Pickup Code Printing** - Large bold centered codes (e.g. "19-4308")
- **Print Profiles** - Pre-configured settings for portraits, landscapes, documents
- **MQTT Integration** - Remote printing via Home Assistant or any MQTT client
- **Status Reading** - Battery level and printer status

## Project Structure

This repo contains:
- **CLI** (`paperang_p2.py`) — command-line interface for direct printing
- **MQTT Client** (`mqtt_print.py`) — MQTT print service for remote printing

Core logic (USB protocol, print functions, fonts, profiles) lives in [paperang-p2-lib](https://github.com/mdj2812/paperang-p2-lib) (installed via pip).

## Installation

### Quick install

```bash
pip3 install paperang-p2-usb
```

### From source

```bash
git clone https://github.com/mdj2812/paperang-p2-usb.git
cd paperang-p2-usb
pip3 install -e .
```

### Or with requirements.txt

```bash
pip3 install -r requirements.txt
```

## Quick Start

```bash
# Print text
paperang-p2 -t "Hello World"

# Or directly
python3 paperang_p2.py -t "Hello World"

# Print image with profile
paperang-p2 -i photo.jpg -p portrait

# Print QR code
paperang-p2 -q "https://example.com"

# List available profiles
paperang-p2 --list-profiles
```

## Command Line Usage

### Print Text

```bash
# Basic text
paperang-p2 -t "Hello World"

# Custom font size and density
paperang-p2 -t "Dark text" -f 48 -d 100

# Chinese/Japanese/Korean text (requires paperang-p2-lib[cjk])
paperang-p2 -t "一二三 ABC" -f 48
```

### Print Image

```bash
# With default settings
paperang-p2 -i photo.jpg

# With profile
paperang-p2 -i photo.jpg -p portrait

# With custom parameters
paperang-p2 -i photo.jpg --threshold 180 --brightness 1.5 --contrast 0.6
```

### Print Pickup Code

Large bold centered text, perfect for printing pickup codes on receipts:

```bash
# Basic pickup code (96px, max density, centered)
paperang-p2 --pickup-code "19-4308"

# Custom code with any format
paperang-p2 --pickup-code "A-1234"
```

Features:
- 96px font size for maximum readability
- Auto-centered on paper
- Maximum heat density (100%) for bold, clear text
- Perfect for courier/parcel pickup codes

### Print QR Code

```bash
# Basic QR code (auto-sized)
paperang-p2 -q "https://example.com"

# Custom size
paperang-p2 -q "https://example.com" --qr-size 400
```

### Test Functions

```bash
# Print test page
paperang-p2 --test

# Pattern test (lines, columns, multi-packet)
paperang-p2 --pattern-test

# Heat density test
paperang-p2 --density-test

# Get status/battery
paperang-p2 --status
paperang-p2 --battery
```

## Print Profiles

Pre-configured settings optimized for different content types:

| Profile | Threshold | Brightness | Contrast | Heat Density | Best For |
|---------|-----------|------------|----------|--------------|----------|
| `portrait` | 180 | 1.5 | 0.6 | 55 | Photos with faces/glasses |
| `landscape` | 150 | 1.1 | 0.8 | 70 | Nature/scenery photos |
| `document` | 128 | 1.0 | 1.0 | 75 | Text documents |
| `high_contrast` | 100 | 1.0 | 1.2 | 85 | Bold/high-contrast images |
| `light` | 200 | 1.3 | 0.5 | 45 | Saving paper/ink |

View all profiles: `paperang-p2 --list-profiles`

## MQTT Integration

Control the printer remotely via MQTT, perfect for Home Assistant integration.

### Setup

```bash
# Start MQTT print service
sudo systemctl start mqtt-print
sudo systemctl enable mqtt-print  # Auto-start on boot
```

### Publishing Print Jobs

```bash
# Print text
mosquitto_pub -h 192.168.99.6 -t 'paperang/print/text' \
  -m '{"content": "Hello from MQTT", "font_size": 24}'

# Print image
mosquitto_pub -h 192.168.99.6 -t 'paperang/print/image' \
  -m '{"url": "http://example.com/photo.jpg", "profile": "portrait"}'

# Print QR code
mosquitto_pub -h 192.168.99.6 -t 'paperang/print/qr' \
  -m '{"content": "https://example.com"}'
```

### Home Assistant

1. Add MQTT integration pointing to `192.168.99.6:1883`
2. Use `mqtt.publish` service in automations:

```yaml
action: mqtt.publish
data:
  topic: paperang/print/text
  payload: '{"content": "Good Morning!", "font_size": 32}'
```

## Python API

> For the full API and protocol details, see [paperang-p2-lib](https://github.com/mdj2812/paperang-p2-lib).

```python
from paperang import PaperangP2

printer = PaperangP2()
printer.connect()

# Print text
printer.print_text("Hello", font_size=24, heat_density=75)

# Print image with custom parameters
printer.print_image("photo.jpg", heat_density=75, threshold=180, brightness=1.5, contrast=0.6)

# Print QR code
printer.print_qr("https://example.com", max_width=500)

# Manual control
printer.set_heat_density(75)
printer.feed(100)
printer.set_paper_type(0)
```

## Troubleshooting

1. **Permission denied:** Add udev rules or use sudo
2. **Device not found:** Check with `lsusb | grep 4348`
3. **Print too light:** Increase heat density (`-d 100`)
4. **Print too dark:** Decrease heat density (`-d 50`)
5. **No response:** Verify printer is powered on with paper

## References

- [java-paperang-p2-usb](https://github.com/hurui200320/java-paperang-p2-usb) - Java implementation
- [python-paperang](https://github.com/tinyprinter/python-paperang) - Python Bluetooth version
- [Paperang protocol blog](https://www.ihcblog.com/miaomiaoji/) - Chinese blog post

## License

MIT License
