#!/bin/bash

# AnonVPN Celery Worker and Beat Startup Script

# Start Redis if not running
echo "Checking Redis status..."
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis server..."
    redis-server --daemonize yes
else
    echo "Redis is already running"
fi

# Wait for Redis to be ready
sleep 2

# Start Celery Worker in background
echo "Starting Celery Worker..."
cd /app/backend
celery -A celery_worker worker --loglevel=info --logfile=/var/log/celery_worker.log 2>&1 &
WORKER_PID=$!
echo "Celery Worker started with PID: $WORKER_PID"

# Start Celery Beat (scheduler) in background  
echo "Starting Celery Beat..."
celery -A celery_worker beat --loglevel=info --logfile=/var/log/celery_beat.log 2>&1 &
BEAT_PID=$!
echo "Celery Beat started with PID: $BEAT_PID"

echo "✅ Celery services started successfully"
echo "Worker PID: $WORKER_PID"
echo "Beat PID: $BEAT_PID"
echo "Logs: /var/log/celery_worker.log and /var/log/celery_beat.log"
