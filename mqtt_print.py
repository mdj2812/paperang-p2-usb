#!/usr/bin/env python3
"""
MQTT Print Client for Paperang P2
Subscribes to MQTT topics and prints messages
"""

import json
import sys
import os
import argparse
import paho.mqtt.client as mqtt
from paperang_p2 import PaperangP2

# MQTT Configuration
MQTT_BROKER = "192.168.99.6"
MQTT_PORT = 1883
MQTT_TOPICS = [
    "paperang/print/text",
    "paperang/print/image",
    "paperang/print/qr"
]

class MqttPrintClient:
    def __init__(self, broker=MQTT_BROKER, port=MQTT_PORT):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.printer = None
        
    def connect_printer(self):
        """Connect to Paperang printer"""
        self.printer = PaperangP2()
        self.printer.connect()
        print("Printer connected")
        
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        print(f"Connected to MQTT broker: {self.broker}:{self.port}")
        for topic in MQTT_TOPICS:
            client.subscribe(topic)
            print(f"Subscribed to: {topic}")
            
    def on_message(self, client, userdata, msg):
        """Callback when message received"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        print(f"Received message on {topic}: {payload[:100]}...")
        
        try:
            data = json.loads(payload)
            self.handle_print(topic, data)
        except json.JSONDecodeError:
            # If not JSON, treat as plain text
            if topic == "paperang/print/text":
                self.print_text({"content": payload})
            elif topic == "paperang/print/qr":
                self.print_qr({"content": payload})
                
    def handle_print(self, topic, data):
        """Handle print request based on topic"""
        if topic == "paperang/print/text":
            self.print_text(data)
        elif topic == "paperang/print/image":
            self.print_image(data)
        elif topic == "paperang/print/qr":
            self.print_qr(data)
            
    def print_text(self, data):
        """Print text"""
        content = data.get("content", "")
        font_size = data.get("font_size", 24)
        heat_density = data.get("heat_density", 75)
        
        if not content:
            print("Error: No content provided for text print")
            return
            
        try:
            self.printer.print_text(content, font_size=font_size, heat_density=heat_density)
            print(f"Printed text: {content[:50]}...")
        except Exception as e:
            print(f"Print error: {e}")
            
    def print_image(self, data):
        """Print image from URL or local path"""
        url = data.get("url") or data.get("path")
        profile = data.get("profile")
        heat_density = data.get("heat_density", 75)
        threshold = data.get("threshold", 180)
        brightness = data.get("brightness", 1.5)
        contrast = data.get("contrast", 0.6)
        
        if not url:
            print("Error: No URL or path provided for image print")
            return
            
        try:
            # Download image if URL
            if url.startswith("http"):
                import urllib.request
                local_path = "/tmp/mqtt_image.jpg"
                urllib.request.urlretrieve(url, local_path)
                url = local_path
                
            # Use profile if specified
            if profile:
                profiles = {
                    "portrait": {"threshold": 180, "brightness": 1.5, "contrast": 0.6, "heat_density": 55},
                    "landscape": {"threshold": 150, "brightness": 1.1, "contrast": 0.8, "heat_density": 70},
                    "document": {"threshold": 128, "brightness": 1.0, "contrast": 1.0, "heat_density": 75},
                    "high_contrast": {"threshold": 100, "brightness": 1.0, "contrast": 1.2, "heat_density": 85},
                    "light": {"threshold": 200, "brightness": 1.3, "contrast": 0.5, "heat_density": 45}
                }
                p = profiles.get(profile, {})
                threshold = p.get("threshold", threshold)
                brightness = p.get("brightness", brightness)
                contrast = p.get("contrast", contrast)
                heat_density = p.get("heat_density", heat_density)
                
            self.printer.print_image(url, heat_density=heat_density, 
                                   threshold=threshold, brightness=brightness, contrast=contrast)
            print(f"Printed image: {url}")
        except Exception as e:
            print(f"Print error: {e}")
            
    def print_qr(self, data):
        """Print QR code"""
        content = data.get("content", "")
        size = data.get("size", 500)
        heat_density = data.get("heat_density", 75)
        
        if not content:
            print("Error: No content provided for QR print")
            return
            
        try:
            self.printer.print_qr(content, heat_density=heat_density, max_width=size)
            print(f"Printed QR: {content[:50]}...")
        except Exception as e:
            print(f"Print error: {e}")
            
    def run(self):
        """Start MQTT client"""
        print(f"Connecting to MQTT broker {self.broker}:{self.port}...")
        self.client.connect(self.broker, self.port, 60)
        
        print("Connecting to printer...")
        self.connect_printer()
        
        print("MQTT Print Client started. Waiting for messages...")
        print("Publish to topics:")
        for topic in MQTT_TOPICS:
            print(f"  - {topic}")
            
        try:
            self.client.loop_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.client.disconnect()


def main():
    parser = argparse.ArgumentParser(description='MQTT Print Client for Paperang P2')
    parser.add_argument('--broker', default=MQTT_BROKER, help='MQTT broker address')
    parser.add_argument('--port', type=int, default=MQTT_PORT, help='MQTT broker port')
    
    args = parser.parse_args()
    
    client = MqttPrintClient(broker=args.broker, port=args.port)
    client.run()


if __name__ == '__main__':
    main()
