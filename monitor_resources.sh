#!/bin/bash
# Resource monitoring script for PressVPN

LOG_FILE="/var/log/remnawave_monitoring.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# CPU usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')

# Memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')

# Disk usage
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

# Docker containers status
CONTAINERS_RUNNING=$(docker ps --format "table {{.Names}}\t{{.Status}}" | grep -c "Up")

# Log the metrics
echo "$DATE - CPU: ${CPU_USAGE}% | Memory: ${MEMORY_USAGE}% | Disk: ${DISK_USAGE}% | Containers: $CONTAINERS_RUNNING" >> "$LOG_FILE"

# Alert if thresholds exceeded
if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
    echo "$DATE - ALERT: High CPU usage: ${CPU_USAGE}%" >> "$LOG_FILE"
fi

if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
    echo "$DATE - ALERT: High Memory usage: ${MEMORY_USAGE}%" >> "$LOG_FILE"
fi

if [ "$DISK_USAGE" -gt 80 ]; then
    echo "$DATE - ALERT: High Disk usage: ${DISK_USAGE}%" >> "$LOG_FILE"
fi
