#!/bin/bash
BASE_URL="http://localhost:20128/v1"
PROXY_URL="http://127.0.0.1:8787"

if curl -sf "$PROXY_URL/health" > /dev/null 2>&1; then
    exit 0
fi

nohup headroom proxy --port 8787 --openai-api-url "$BASE_URL" > /tmp/headroom.log 2>&1 &
sleep 2
echo "headroom proxy started → $PROXY_URL (upstream: $BASE_URL)"
