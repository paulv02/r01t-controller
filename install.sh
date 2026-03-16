#!/bin/bash
set -e

#curl -s https://raw.githubusercontent.com/paulv02/r01t-controller/main/install.sh -o install.sh
#bash install.sh


apt-get update -qq
apt-get install -y python3-pip python3-venv git

git clone https://github.com/paulv02/r01t-controller /opt/r01t-controller

cd /opt/r01t-controller
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cat > /etc/systemd/system/r01t-controller.service << EOF
[Unit]
Description=r01t Controller
After=network.target

[Service]
User=root
WorkingDirectory=/opt/r01t-controller
ExecStart=/opt/r01t-controller/venv/bin/uvicorn main:app --host 0.0.0.0 --port 7777
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable r01t-controller
systemctl start r01t-controller

echo "R01T Controller installed and running on port 7777"