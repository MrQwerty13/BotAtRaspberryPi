#!/bin/bash

CONFIG="/home/mikhail/vpn/config.ovpn"

echo "Starting OpenVPN..."

sudo openvpn --config "$CONFIG" --daemon

echo "VPN started"