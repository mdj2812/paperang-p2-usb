# Paperang P2 USB Printer

Control Paperang P2 thermal printer via USB on Linux systems, with Home Assistant integration via MQTT.

Based on [hurui200320/java-paperang-p2-usb](https://github.com/hurui200320/java-paperang-p2-usb) protocol implementation.

## Features

- **Text Printing** - CJK font support (Chinese, Japanese, Korean) with adjustable size
- **Image Printing** - Adjustable threshold, brightness, and contrast
- **QR Code Printing** - Auto-sized to fill paper width
- **Print Profiles** - Pre-configured settings for portraits, landscapes, documents
- **MQTT Integration** - Remote printing via Home Assistant or any MQTT client
- **Status Reading** - Battery level and printer status

## Quick Start

```bash
# Install dependencies
sudo apt-get install python3-usb python3-pil python3-qrcode
pip3 install pyusb pillow qrcode[pil]

# Print text
sudo python3 paperang_p2.py -t "Hello World"

# Print image with profile
sudo python3 paperang_p2.py -i photo.jpg -p portrait

# Print QR code
sudo python3 paperang_p2.py -q "https://example.com"

# List available profiles
python3 paperang_p2.py --list-profiles
```

## Command Line Usage

### Print Text

```bash
# Basic text
sudo python3 paperang_p2.py -t "Hello World"

# Custom font size and density
sudo python3 paperang_p2.py -t "Dark text" -f 48 -d 100

# Chinese/Japanese/Korean text
sudo python3 paperang_p2.py -t "一二三 ABC" -f 48
```

### Print Image

```bash
# With default settings
sudo python3 paperang_p2.py -i photo.jpg

# With profile
sudo python3 paperang_p2.py -i photo.jpg -p portrait

# With custom parameters
sudo python3 paperang_p2.py -i photo.jpg --threshold 180 --brightness 1.5 --contrast 0.6
```

### Print QR Code

```bash
# Basic QR code (auto-sized)
sudo python3 paperang_p2.py -q "https://example.com"

# Custom size
sudo python3 paperang_p2.py -q "https://example.com" --qr-size 400
```

### Test Functions

```bash
# Print test page
sudo python3 paperang_p2.py --test

# Pattern test (lines, columns, multi-packet)
sudo python3 paperang_p2.py --pattern-test

# Heat density test
sudo python3 paperang_p2.py --density-test

# Get status/battery
sudo python3 paperang_p2.py --status
sudo python3 paperang_p2.py --battery
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

View all profiles: `python3 paperang_p2.py --list-profiles`

## MQTT Integration

Control the printer remotely via MQTT, perfect for Home Assistant integration.

### Setup

```bash
# Install MQTT client library
sudo pip3 install paho-mqtt

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

```python
from paperang_p2 import PaperangP2

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

## Protocol Details

- **Vendor ID:** 0x4348
- **Product ID:** 0x5584
- **Print width:** 576 pixels (72 bytes/line)
- **Packet size:** 14 lines per packet (1008 bytes)

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

Custom seed `0x35769521` (standard CRC32 uses `0x00000000`).

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
