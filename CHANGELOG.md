# Changelog

## [Unreleased]

## [2.3.0-custom] - 2025-08-27

### Added
- User creation during panel synchronization (upstream v2.2.1)
- Enhanced sync statistics with localization support
- Markdown escaping for user display names in admin panel
- Version management system
- GitHub Actions workflow for automated Docker builds with versioning
- Comprehensive changelog tracking

### Fixed  
- Telegram markdown parsing errors in admin user list (issue with special characters like `_` and `'`)
- Panel synchronization now creates missing users with valid Telegram IDs

### Changed
- Enhanced error handling for user list display
- Improved sync logging with detailed statistics including users created
- Updated localization strings for sync feedback
- Sync statistics now show users created vs. just found

## Previous versions
- Based on upstream remnawave-tg-shop with custom modifications
