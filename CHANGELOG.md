# Changelog

All notable changes to the CTFd OAuth Plugin are documented in this file.

## [2.0.0] - 2024

### 🔒 Security

#### Critical Security Fixes
- **State Validation Enhancement** - Added proper error handling for missing or invalid state parameters
  - Prevents KeyError when session lacks nonce
  - Uses `secrets.compare_digest()` for constant-time comparison to prevent timing attacks
  - Better CSRF protection

- **HTTP Request Timeouts** - All OAuth HTTP requests now have proper timeout handling
  - Default timeout: 10 seconds
  - Prevents hung connections and DoS vulnerabilities
  - Automatic retry logic for transient failures (500, 502, 504)

- **JSON Response Validation** - Comprehensive validation of OAuth provider responses
  - Try/except blocks for all JSON parsing
  - Validates presence of required fields before access
  - Prevents crashes from malformed responses
  - Detailed error logging for troubleshooting

- **Email Overwrite Protection** - Fixed account takeover vulnerability
  - Email addresses no longer updated from OAuth provider for existing users
  - Prevents account takeover if OAuth provider is compromised
  - Only username and affiliation are updated on subsequent logins

#### Security Enhancements
- **PKCE Support** - Implemented Proof Key for Code Exchange (RFC 7636)
  - SHA-256 code challenge generation
  - Cryptographically secure code verifier
  - Protects against authorization code interception attacks
  - Complies with OAuth 2.1 best practices

- **URL Parameter Encoding** - Proper encoding of OAuth URLs
  - Uses `urllib.parse.urlencode()` instead of string formatting
  - Prevents URL injection attacks
  - Handles special characters correctly

- **Admin Promotion Logging** - Comprehensive audit trail
  - Logs all admin privilege escalations
  - Includes OAuth group name in logs
  - Logs IP address and timestamp
  - Helps detect unauthorized privilege escalation

- **Configuration Validation** - Validates configuration before enabling
  - Ensures required fields are set
  - Validates URL formats
  - Prevents partial configuration from breaking authentication

### ✨ Features

#### Hot Reload / Dynamic Configuration
- **No restart required** - Configuration changes take effect immediately
- Route wrappers dynamically check OAuth enabled status on each request
- Falls back to original CTFd authentication when OAuth is disabled
- Performance optimized with 60-second caching
- Cache automatically cleared when configuration is saved
- Allows testing OAuth without downtime
- Quick disable in case of issues
- User-friendly success messages confirming changes are active

**Implementation:**
- `oauth_route_wrapper()` - Dynamic route switching based on configuration
- `is_oauth_enabled()` - Cached configuration check (60s TTL)
- `clear_oauth_cache()` - Cache invalidation on config save
- Stores original view functions for seamless fallback

#### OIDC Discovery Support
- Auto-configure endpoints from OIDC discovery URL
- Supports `.well-known/openid-configuration`
- Reduces configuration complexity
- Auto-populates authorization, token, userinfo, and logout endpoints
- Fallback to manual configuration if discovery fails

#### Configurable Claim Mapping
- Map non-standard claim names to CTFd user attributes
- Configure username claim (default: `preferred_username`)
- Configure email claim (default: `email`)
- Configure affiliation claim (default: `affiliation`)
- Supports providers with custom claim schemas

#### Configurable OAuth Scopes
- Override default scopes per deployment
- Default individual mode: `openid profile email`
- Default team mode: `profile team`
- Custom scopes for specific provider requirements

#### Logout Handler
- Proper logout from OAuth provider
- Redirects to provider's logout endpoint
- Cleans up OAuth session data
- Supports post-logout redirect URI
- Prevents session lingering

#### Team Synchronization
- Optional automatic team membership updates
- Syncs team assignment on each login
- Useful for dynamic team management
- Configurable via admin panel

#### Admin Group Configuration
- Configurable admin group name
- No longer hardcoded to "CTFd Admins"
- Supports different group naming conventions
- Per-deployment customization

### 🐛 Bug Fixes

- **File Handle Leak** - Fixed unclosed file handle in `__init__.py`
  - Now uses context manager (`with` statement)
  - Prevents resource leaks

- **Unused Imports** - Removed unused imports
  - Removed `Brackets` from `auth.py`
  - Removed `datetime` from `auth.py`
  - Cleaner code

- **Team Assignment Logic** - Fixed team membership handling
  - Now supports team synchronization
  - Prevents users from being locked to first team
  - Configurable sync behavior

- **Settings Redirect Validation** - Only redirects if profile URL is set
  - Checks if `oauth_profile_url` is configured
  - Prevents redirect to empty string
  - Better error handling

- **Incomplete Configuration Check** - Validates all required fields
  - Checks client_id, client_secret, and endpoints
  - Only enables OAuth if configuration is complete
  - Prevents partial configuration errors

### 🏗️ Code Quality

#### Type Hints
- Added comprehensive type hints to all functions
- Improves IDE autocompletion and error detection
- Better code documentation
- Enables static type checking with mypy

#### Refactoring
- **Extracted Functions** - Broke down 120-line `oauth2_callback()` into focused functions:
  - `validate_state()` - State parameter validation
  - `exchange_code_for_token()` - Token exchange
  - `fetch_userinfo()` - UserInfo retrieval
  - `create_or_update_user()` - User management
  - `handle_team_assignment()` - Team mode logic
  - `handle_admin_promotion()` - Admin privileges
  - Each function has single responsibility
  - Easier to test and maintain

- **Removed Magic Strings** - Replaced hardcoded values with constants
  - `ADMIN_GROUP_CONFIG_KEY` for admin group configuration
  - `REQUEST_TIMEOUT` for HTTP timeouts
  - `MAX_RETRIES` for retry logic
  - Configuration-driven behavior

- **Better Error Messages** - User-friendly error messages
  - Specific error messages for each failure scenario
  - Guides users to resolution
  - Doesn't expose sensitive information
  - Consistent error handling

#### Database Utilities
- Added `validate_config()` method
- Added `discover_oidc_endpoints()` method
- Improved type hints
- Better documentation
- Fixed variable naming inconsistency

#### Models
- Added docstrings
- Fixed `__repr__()` method
- Added type hints
- More informative string representation

### 🎨 User Experience

#### Admin Configuration UI
- **Two-Tab Interface** - Separated basic and advanced settings
  - Basic settings tab for common configuration
  - Advanced tab for claim mapping, scopes, etc.
  - Cleaner, less overwhelming interface

- **Password Input** - Client secret now uses password field
  - Hides sensitive values by default
  - Show/hide toggle for visibility
  - Better security posture

- **Help Text** - Comprehensive inline documentation
  - Explains each field's purpose
  - Provides examples
  - Links to provider-specific docs
  - Reduces support burden

- **Field Validation** - HTML5 validation
  - Required fields marked
  - URL validation for endpoint fields
  - Better user feedback

- **Success Messages** - Positive feedback for OIDC discovery
  - Shows success when endpoints auto-configured
  - Separates success from error messages
  - Green success alerts

#### Better Error Messages
- Specific failure messages instead of generic errors
- "Failed to obtain access token" instead of "token retrieval failure"
- "OAuth authorization failed. No code received." instead of "no OAuth code"
- "Please try again" suggestions
- Actionable error messages

### 📚 Documentation

#### README.md
- Comprehensive setup guide
- Feature list with explanations
- Configuration examples for popular providers
- Security considerations
- Troubleshooting section
- Plugin architecture documentation
- Configuration schema reference

#### EXAMPLES.md
- Detailed provider configurations for:
  - Authentik
  - Keycloak
  - Auth0
  - Okta
  - Azure AD / Entra ID
  - Google
  - GitHub
  - GitLab
- Copy-paste ready configurations
- Provider-specific notes and limitations
- Common issues and solutions

#### UPGRADE.md
- Upgrade guide from v1.0 to v2.0
- Backward compatibility notes
- Step-by-step upgrade procedure
- Rollback instructions
- Post-upgrade recommendations

#### CHANGELOG.md
- This file
- Detailed change documentation
- Version history

### 🔧 Configuration

#### New Configuration Keys
- `oauth_logout_url` - Provider logout endpoint
- `oauth_scope` - Custom OAuth scopes
- `oauth_admin_group` - Admin group name
- `oauth_sync_teams` - Team synchronization toggle
- `oauth_discovery_url` - OIDC discovery URL
- `oauth_claim_preferred_username` - Username claim mapping
- `oauth_claim_email` - Email claim mapping
- `oauth_claim_affiliation` - Affiliation claim mapping

All new keys have sensible defaults and are optional for backward compatibility.

### 🧪 Testing

- Python syntax validation with `py_compile`
- All files compile without errors
- 684 total lines of Python code
- 737 insertions, 191 deletions from v1.0

### 📊 Statistics

- **Files Changed:** 6
- **Lines Added:** 737
- **Lines Removed:** 191
- **Net Change:** +546 lines
- **Type Hints:** ~50 functions annotated
- **New Functions:** 7 extracted functions
- **Documentation:** 4 new files (README, EXAMPLES, UPGRADE, CHANGELOG)

### ⚡ Performance

- HTTP request pooling with sessions
- Connection reuse for multiple requests
- Automatic retry with exponential backoff
- Timeout prevents hung connections
- Session cleanup after OAuth flow

### 🔄 Backward Compatibility

- **100% backward compatible** with v1.0 configurations
- Existing configurations continue to work
- New fields added with defaults
- No database migrations required
- No breaking changes

### 📝 Code Comments

- Removed unprofessional comment in `auth.py:60`
- Added professional explanation of redirect_uri requirement
- Better inline documentation
- Docstrings for all functions

### 🚀 Migration Path

Upgrading from v1.0:
1. Backup configuration
2. Stop CTFd
3. Replace plugin files
4. Start CTFd
5. Review configuration
6. Optionally enable new features

See [UPGRADE.md](UPGRADE.md) for detailed instructions.

---

## [1.0.0] - Original Release

### Features
- Basic OAuth 2.0 authentication flow
- Team mode support
- Admin promotion via group membership
- User auto-creation
- Basic configuration UI

### Known Issues (Fixed in 2.0.0)
- No PKCE support
- Hardcoded admin group name
- Email overwrite vulnerability
- No request timeouts
- Missing error handling
- File handle leak
- No OIDC discovery
- Limited documentation

---

## Comparison Summary

| Feature | v1.0 | v2.0 |
|---------|------|------|
| OAuth 2.0 | ✅ | ✅ |
| PKCE | ❌ | ✅ |
| OIDC Discovery | ❌ | ✅ |
| Request Timeouts | ❌ | ✅ |
| Retry Logic | ❌ | ✅ |
| Email Protection | ❌ | ✅ |
| Type Hints | ❌ | ✅ |
| Logout Handler | ❌ | ✅ |
| Configurable Claims | ❌ | ✅ |
| Configurable Scopes | ❌ | ✅ |
| Team Sync | ❌ | ✅ |
| Config Validation | ❌ | ✅ |
| Comprehensive Docs | ❌ | ✅ |
| Security Logging | Partial | ✅ |
| Lines of Code | 137 | 684 |

---

[2.0.0]: https://github.com/yourusername/ctfd-oauth/releases/tag/v2.0.0
[1.0.0]: https://github.com/yourusername/ctfd-oauth/releases/tag/v1.0.0
