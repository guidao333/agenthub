#!/bin/bash
cd /opt/agenthub/backend
pip3 install --break-system-packages -r requirements.txt > /tmp/pip_install.log 2>&1
echo "EXIT_CODE=$?" >> /tmp/pip_install.log
