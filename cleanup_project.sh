#!/bin/bash

# Cleanup script for remnawave-tg-bot project
# Removes obsolete files and keeps only production-ready structure

echo "🧹 Starting project cleanup..."

# Remove old deployment scripts
rm -f backup.sh
rm -f bot-commands-curl.sh  
rm -f cleanup_files.bat
rm -f deploy_support_system.bat
rm -f deploy_updates.bat
rm -f deploy_updates.sh
rm -f fix_all_errors.bat
rm -f fix_broadcast_keyboard.bat
rm -f fix_imports.bat
rm -f fix_imports.sh
rm -f fix_notification_service.bat
rm -f monitor_resources.sh
rm -f security_cleanup.sh
rm -f setup_landing.sh

# Remove old documentation files
rm -f final-setup-instructions.md
rm -f MISSING_LOCALIZATION_KEYS.md
rm -f pressvpn-shop-setup.md
rm -f readme-bot.md
rm -f "Terms of servcie.md"
rm -f UPDATE_DEPLOYMENT.md

# Keep essential files structure
echo "✅ Keeping essential files:"
echo "   - Core application (bot/, config/, db/, main.py)"
echo "   - Docker configuration (docker-compose.yml, Dockerfile)" 
echo "   - Documentation (README.md, CHANGELOG.md)"
echo "   - Configuration (locales/, landing/, requirements.txt)"
echo "   - Version management (VERSION, .github/)"

echo "🗑️  Removed obsolete files:"
echo "   - Old batch deployment scripts"
echo "   - Temporary shell scripts" 
echo "   - Outdated documentation"
echo "   - Legacy setup files"

echo "📁 Final clean project structure ready!"
