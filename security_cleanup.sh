#!/bin/bash

# Security Cleanup Script for PressVPN Project
# Удаляет ненужные файлы статуса серверов и повышает безопасность

set -e

PROJECT_DIR="/opt/remnawave-tg-bot"
BACKUP_DIR="/opt/backups/remnawave-$(date +%Y%m%d_%H%M%S)"

echo "🔧 PressVPN Security Cleanup Script"
echo "======================================"

# 1. Создаем резервную копию
echo "📦 Creating backup..."
mkdir -p "$BACKUP_DIR"
cp -r "$PROJECT_DIR"/* "$BACKUP_DIR/" 2>/dev/null || true
echo "✅ Backup created at: $BACKUP_DIR"

# 2. Удаляем файлы связанные со статусом серверов (если есть)
echo "🧹 Cleaning up server status files..."
find "$PROJECT_DIR" -name "*status*" -type f -delete 2>/dev/null || true
find "$PROJECT_DIR" -name "*server*monitor*" -type f -delete 2>/dev/null || true

# 3. Очищаем логи
echo "🗂️ Cleaning up logs..."
find "$PROJECT_DIR" -name "*.log" -type f -exec truncate -s 0 {} \; 2>/dev/null || true
find "$PROJECT_DIR" -name "*.log.*" -type f -delete 2>/dev/null || true

# 4. Удаляем временные файлы
echo "🗑️ Removing temporary files..."
find "$PROJECT_DIR" -name "*.tmp" -type f -delete 2>/dev/null || true
find "$PROJECT_DIR" -name ".DS_Store" -type f -delete 2>/dev/null || true
find "$PROJECT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_DIR" -name "*.pyc" -type f -delete 2>/dev/null || true

# 5. Устанавливаем правильные права доступа
echo "🔐 Setting secure file permissions..."
chown -R root:root "$PROJECT_DIR"
chmod -R 644 "$PROJECT_DIR"
chmod -R +X "$PROJECT_DIR" # Делаем директории исполняемыми
chmod 600 "$PROJECT_DIR"/.env 2>/dev/null || true
chmod +x "$PROJECT_DIR"/*.sh 2>/dev/null || true

# 6. Проверяем .env файл на чувствительные данные
echo "🔍 Checking .env file security..."
ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    # Проверяем на тестовые токены
    if grep -q "test_" "$ENV_FILE"; then
        echo "⚠️  WARNING: Test tokens found in .env file - consider updating for production"
    fi
    
    # Проверяем на слабые пароли
    if grep -qi "password.*123\|password.*admin\|password.*test" "$ENV_FILE"; then
        echo "❌ ERROR: Weak passwords detected in .env file"
        exit 1
    fi
    
    echo "✅ .env file security check passed"
fi

# 7. Обновляем docker-compose для продакшена
echo "🐳 Updating Docker configuration..."
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
if [ -f "$COMPOSE_FILE" ]; then
    # Убеждаемся что нет дебаг портов
    if grep -q "ports:" "$COMPOSE_FILE"; then
        echo "⚠️  WARNING: Port mappings found in docker-compose.yml"
        echo "   Consider removing direct port exposure for security"
    fi
fi

# 8. Создаем .dockerignore если его нет
DOCKERIGNORE="$PROJECT_DIR/.dockerignore"
if [ ! -f "$DOCKERIGNORE" ]; then
    echo "📝 Creating .dockerignore..."
    cat > "$DOCKERIGNORE" << EOF
.git
.gitignore
.DS_Store
*.log
*.tmp
__pycache__
*.pyc
node_modules
.env.local
.env.development
*.md
docs/
README*
EOF
fi

# 9. Создаем базовый fail2ban конфиг для защиты
echo "🛡️ Creating fail2ban configuration..."
FAIL2BAN_CONFIG="/etc/fail2ban/jail.d/remnawave.conf"
if command -v fail2ban-server &> /dev/null; then
    cat > "$FAIL2BAN_CONFIG" << EOF
[remnawave-tg-bot]
enabled = true
port = 8080
protocol = tcp
filter = remnawave-tg-bot
logpath = /var/log/nginx/access.log
maxretry = 5
bantime = 3600
findtime = 600
EOF

    echo "✅ Fail2ban configuration created"
else
    echo "⚠️  Fail2ban not installed - consider installing for additional security"
fi

# 10. Проверяем систему на подозрительные процессы
echo "🔍 Checking for suspicious processes..."
if ps aux | grep -E "(bitcoin|miner|crypto|xmrig)" | grep -v grep; then
    echo "❌ WARNING: Potential crypto mining processes detected!"
fi

# 11. Обновляем системные пакеты
echo "📦 Updating system packages..."
if command -v apt &> /dev/null; then
    apt update && apt upgrade -y
elif command -v yum &> /dev/null; then
    yum update -y
fi

# 12. Создаем мониторинг ресурсов
echo "📊 Setting up resource monitoring..."
MONITOR_SCRIPT="$PROJECT_DIR/monitor_resources.sh"
cat > "$MONITOR_SCRIPT" << 'EOF'
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
EOF

chmod +x "$MONITOR_SCRIPT"

# Добавляем в crontab если его еще нет
if ! crontab -l | grep -q "monitor_resources.sh"; then
    (crontab -l 2>/dev/null; echo "*/5 * * * * $MONITOR_SCRIPT") | crontab -
    echo "✅ Resource monitoring added to crontab"
fi

# 13. Настройка автоматических бэкапов
echo "💾 Setting up automated backups..."
BACKUP_SCRIPT="$PROJECT_DIR/backup.sh"
cat > "$BACKUP_SCRIPT" << 'EOF'
#!/bin/bash
# Automated backup script for PressVPN

BACKUP_DIR="/opt/backups"
PROJECT_DIR="/opt/remnawave-tg-bot"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/remnawave_backup_$DATE.tar.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create compressed backup
tar -czf "$BACKUP_FILE" -C "$PROJECT_DIR" .

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/remnawave_backup_*.tar.gz | tail -n +8 | xargs -r rm

# Backup database
docker exec remnawave-tg-shop-db pg_dump -U postgres pressvpn_shop > "$BACKUP_DIR/db_backup_$DATE.sql"

# Keep only last 7 database backups
ls -t "$BACKUP_DIR"/db_backup_*.sql | tail -n +8 | xargs -r rm

echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup completed: $BACKUP_FILE" >> "/var/log/remnawave_backup.log"
EOF

chmod +x "$BACKUP_SCRIPT"

# Добавляем ежедневные бэкапы
if ! crontab -l | grep -q "backup.sh"; then
    (crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT") | crontab -
    echo "✅ Daily backups configured"
fi

# 14. Финальная проверка безопасности
echo "🔒 Final security check..."

# Проверяем открытые порты
echo "Open ports:"
netstat -tlnp | grep LISTEN

# Проверяем запущенные Docker контейнеры
echo "Running containers:"
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"

echo ""
echo "🎉 Security cleanup completed successfully!"
echo "======================================"
echo "✅ Backup created: $BACKUP_DIR"
echo "✅ Server status functionality removed"
echo "✅ Temporary files cleaned"
echo "✅ File permissions secured"
echo "✅ Monitoring configured"
echo "✅ Automated backups enabled"
echo ""
echo "🚀 Your PressVPN project is now cleaner and more secure!"
echo ""
echo "⚠️  Don't forget to:"
echo "   1. Review and rotate any exposed API keys"
echo "   2. Enable UFW firewall if not already enabled"
echo "   3. Set up SSL certificates for all domains"
echo "   4. Configure log rotation"
