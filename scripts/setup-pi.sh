#!/usr/bin/env bash
# ELIOT Raspberry Pi setup script
# Configures Pi as the face/display module connected to Jetson
set -euo pipefail

PI_HOSTNAME="${1:-eliot-pi}"
JETSON_HOST="${2:-eliot-jetson}"

echo "=== ELIOT Raspberry Pi Setup ==="

# Update system
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-pip python3-venv \
    mosquitto-clients \
    libcamera-tools \
    pulseaudio \
    ffmpeg \
    git

# Create eliot user if not exists
if ! id "eliot" &>/dev/null; then
    sudo useradd -m -s /bin/bash eliot
fi

# Setup project directory
ELIOT_PI_DIR="/home/eliot/eliot-pi"
mkdir -p "$ELIOT_PI_DIR"
cd "$ELIOT_PI_DIR"

# Create Python venv
python3 -m venv venv
source venv/bin/activate
pip install --quiet \
    websockets \
    paho-mqtt \
    pillow \
    numpy

# Create avatar display script
cat > avatar_display.py << 'AVATAR_SCRIPT'
#!/usr/bin/env python3
"""ELIOT Avatar Display - Receives state from Jetson and renders on Pi TFT."""
import asyncio
import json
import logging
import websockets

JETSON_WS = "ws://JETSON_HOST:8765/avatar"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("avatar_display")

async def receive_state():
    async with websockets.connect(JETSON_WS) as ws:
        logger.info(f"Connected to {JETSON_WS}")
        async for message in ws:
            state = json.loads(message)
            logger.info(f"State: {state['state']} | Emotion: {state['emotion']} | Lip: {state['lip_sync']:.2f}")

if __name__ == "__main__":
    asyncio.run(receive_state())
AVATAR_SCRIPT

sed -i "s/JETSON_HOST/$JETSON_HOST/g" avatar_display.py
chmod +x avatar_display.py

# Create MQTT status listener
cat > mqtt_listener.py << 'MQTT_SCRIPT'
#!/usr/bin/env python3
"""ELIOT MQTT listener for Pi <-> Jetson communication."""
import json
import paho.mqtt.client as mqtt

JETSON_HOST = "JETSON_HOST"
TOPICS = ["eliot/avatar/state", "eliot/system/status", "eliot/ui/touch"]

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT at {JETSON_HOST}")
    for topic in TOPICS:
        client.subscribe(topic)

def on_message(client, userdata, msg):
    print(f"[{msg.topic}] {msg.payload.decode()}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(JETSON_HOST, 1883, 60)
client.loop_forever()
MQTT_SCRIPT

sed -i "s/JETSON_HOST/$JETSON_HOST/g" mqtt_listener.py

# Create systemd service for avatar display
sudo tee /etc/systemd/system/eliot-avatar.service > /dev/null << EOF
[Unit]
Description=ELIOT Avatar Display
After=network.target

[Service]
Type=simple
User=eliot
WorkingDirectory=$ELIOT_PI_DIR
ExecStart=$ELIOT_PI_DIR/venv/bin/python avatar_display.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable eliot-avatar.service

echo ""
echo "=== Setup Complete ==="
echo "Avatar display: $ELIOT_PI_DIR/avatar_display.py"
echo "MQTT listener:  $ELIOT_PI_DIR/mqtt_listener.py"
echo "Start with:     sudo systemctl start eliot-avatar"
echo ""
