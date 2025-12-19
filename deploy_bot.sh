#!/bin/bash
# Deploy Trading Bot to OCI Instance

echo "Packaging bot..."
tar -czf trading_bot.tar.gz --exclude='trading_bot/data' --exclude='trading_bot/logs' trading_bot/

echo "Uploading to Trading-Bot-Main..."
scp -i /Users/mohankrishna/.ssh/google_compute_engine -o StrictHostKeyChecking=no trading_bot.tar.gz ubuntu@129.153.60.198:~

echo "Extracting and Restarting on remote server..."
ssh -i /Users/mohankrishna/.ssh/google_compute_engine -o StrictHostKeyChecking=no ubuntu@129.153.60.198 "tar -xzf trading_bot.tar.gz && cd trading_bot && sudo docker compose up -d --build && echo '✅ Deployed and Restarted!'"

echo "🚀 Deployment Complete!"
