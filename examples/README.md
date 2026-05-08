# Examples

## MQTT Print Client (`mqtt_print.py`)

This example shows how to use paperang-p2-lib to build an MQTT-based
print service for remote printing (e.g. Home Assistant integration).

### Install dependencies

```bash
pip install paho-mqtt
```

### Run

```bash
python3 examples/mqtt_print.py
```

### Usage

Publish print jobs from any MQTT client:

```bash
# Print text
mosquitto_pub -h <broker> -t 'paperang/print/text' \
  -m '{"content": "Hello from MQTT", "font_size": 24}'

# Print image
mosquitto_pub -h <broker> -t 'paperang/print/image' \
  -m '{"url": "http://example.com/photo.jpg", "profile": "portrait"}'

# Print QR code
mosquitto_pub -h <broker> -t 'paperang/print/qr' \
  -m '{"content": "https://example.com"}'
```
