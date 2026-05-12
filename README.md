# Paperang P2 USB Printer

Python CLI and library for the Paperang P2 thermal printer. Supports printing text, images, QR codes, pickup codes, and reading all printer telemetry.

## Quick Start

```bash
# Print text
python3 paperang_p2.py text "Hello World"
python3 paperang_p2.py text "你好世界" --font-size 48 --density 80

# Print image (local file or URL)
python3 paperang_p2.py image photo.jpg --profile high_contrast
python3 paperang_p2.py image https://example.com/photo.jpg --profile portrait

# Print QR code
python3 paperang_p2.py qr "https://example.com" --qr-size 400

# Print pickup code
python3 paperang_p2.py pickup "19-4308"

# Print test pages
python3 paperang_p2.py test
python3 paperang_p2.py pattern
python3 paperang_p2.py density

# Read telemetry
python3 paperang_p2.py info              # all fields
python3 paperang_p2.py info battery      # just battery
python3 paperang_p2.py info version      # firmware version
python3 paperang_p2.py info voltage      # battery voltage mV
python3 paperang_p2.py info temperature  # head temp
python3 paperang_p2.py info model        # printer model
python3 paperang_p2.py info serial       # serial number

# Feed paper
python3 paperang_p2.py feed 50

# List print profiles
python3 paperang_p2.py profile list
```

## Subcommands

### `text <content>`

Print text.

| Flag | Default | Description |
|------|---------|-------------|
| `--font-size N` | 24 | Font size (12–96) |
| `--density N` | 75 | Heat density (0–100) |
| `--profile NAME` | — | Use image profile settings |

### `image <path|url>`

Print image from local file or remote URL.

| Flag | Default | Description |
|------|---------|-------------|
| `--profile NAME` | — | Image profile |
| `--density N` | 75 | Heat density (0–100) |
| `--threshold N` | 128 | Binarization threshold (0–255) |
| `--brightness N` | 1.0 | Brightness multiplier |
| `--contrast N` | 1.0 | Contrast multiplier |

### `qr <content>`

Print QR code.

| Flag | Default | Description |
|------|---------|-------------|
| `--qr-size N` | 500 | QR code size in px (100–576) |
| `--density N` | 75 | Heat density (0–100) |
| `--profile NAME` | — | Use image profile settings |

### `pickup <code>`

Print large pickup code.

| Flag | Default | Description |
|------|---------|-------------|
| `--density N` | 100 | Heat density (0–100) |
| `--profile NAME` | — | Use image profile settings |

### `test`

Print built-in test page.

### `pattern`

Print pattern test (line/column/multi-packet).

### `density`

Print heat density test pattern.

### `info [field]`

Read printer telemetry. Without arguments, shows all fields.

Available fields: `battery`, `status`, `voltage`, `temperature`, `heat`, `paper`, `version`, `model`, `serial`, `board`, `hw`, `mac`, `country`, `max_gap`, `power_down`, `factory`

### `feed [lines]`

Feed paper. Default 100 lines.

### `profile list`

List available print profiles.

## Profiles

Profiles are loaded from `profiles.json` in the script directory. Each profile can specify:

```json
{
  "portrait": {
    "threshold": 180,
    "brightness": 1.5,
    "contrast": 0.6,
    "heat_density": 80
  }
}
```

CLI flags override profile settings.

## Requirements

- Python 3.8+
- `paperang-p2-lib >= 0.3.6`
- USB access to Paperang P2 printer (may need `sudo`)

## License

MIT
