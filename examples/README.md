# Examples

## MQTT Print Client (`mqtt_print.py`)

This example shows how to use paperang-p2-lib to build an MQTT-based
print service for remote printing (e.g. Home Assistant integration).

### Install dependencies

```bash
pip install paho-mqtt
```

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
