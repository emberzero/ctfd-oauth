# Upgrade Guide

## Upgrading from Version 1.0 to 2.0

Version 2.0 includes significant improvements to security, features, and code quality. This guide will help you upgrade safely.

### Breaking Changes

**None!** Version 2.0 is backward compatible with version 1.0 configurations. Your existing configuration will continue to work.

### What's Changed

#### Database Schema

**No database migrations required.** New configuration fields are automatically created with default values when the plugin loads.

The following new configuration keys will be added:
- `oauth_logout_url`
- `oauth_scope`
- `oauth_admin_group`
- `oauth_sync_teams`
- `oauth_discovery_url`
- `oauth_claim_preferred_username`
- `oauth_claim_email`
- `oauth_claim_affiliation`

Your existing configuration values remain unchanged.

#### Security Improvements

1. **PKCE is now enabled by default**
   - If your OAuth provider doesn't support PKCE, it will gracefully ignore the PKCE parameters
   - No action required

2. **State validation enhanced**
   - Uses cryptographically secure token generation
   - Constant-time comparison to prevent timing attacks
   - No action required

3. **Request timeouts added**
   - All OAuth HTTP requests now have a 10-second timeout
   - Automatic retries on transient failures
   - No action required

### Upgrade Steps

#### Step 1: Backup Your Configuration

Before upgrading, backup your OAuth configuration:

```bash
# If using SQLite
sqlite3 /path/to/ctfd.db "SELECT * FROM oauthconfig;" > oauth_config_backup.sql

# If using MySQL/MariaDB
mysqldump -u user -p ctfd oauthconfig > oauth_config_backup.sql

# If using PostgreSQL
pg_dump -U user -t oauthconfig ctfd > oauth_config_backup.sql
```

#### Step 2: Stop CTFd

```bash
docker-compose down
# or
systemctl stop ctfd
```

#### Step 3: Replace Plugin Files

```bash
# Backup old plugin
mv /path/to/CTFd/CTFd/plugins/ctfd-oauth /path/to/CTFd/CTFd/plugins/ctfd-oauth.old

# Copy new plugin
cp -r ctfd-oauth /path/to/CTFd/CTFd/plugins/
```

#### Step 4: Start CTFd

```bash
docker-compose up -d
# or
systemctl start ctfd
```

The plugin will automatically:
1. Detect the upgrade
2. Create new configuration fields with defaults
3. Preserve all existing configuration

#### Step 5: Review Configuration

1. Navigate to `/admin/oauth2`
2. Review your configuration
3. Optionally configure new features:
   - Add **Logout URL** for proper logout handling
   - Add **Discovery URL** for OIDC auto-configuration
   - Configure **Custom Scopes** if needed
   - Set up **Claim Mapping** for non-standard providers

### New Features You Can Enable

#### OIDC Discovery

If your provider supports OIDC discovery, you can simplify your configuration:

1. Navigate to **Admin Panel > OAuth Configuration**
2. Enter your **Discovery URL** (e.g., `https://idp.example.com/.well-known/openid-configuration`)
3. Click **Save Configuration**
4. Endpoints will be auto-populated

#### Logout URL

Enable proper logout handling:

1. Find your provider's logout endpoint
2. Enter it in **Logout URL** field
3. Users will now be logged out from the provider when logging out of CTFd

#### Custom Claim Mapping

If your provider uses non-standard claim names:

1. Navigate to **Advanced** tab
2. Configure claim mappings:
   - **Username Claim**
   - **Email Claim**
   - **Affiliation Claim**

#### Team Synchronization

Enable automatic team updates on each login:

1. Navigate to **Advanced** tab
2. Set **Sync Team Membership** to **Enabled**

### Testing After Upgrade

#### 1. Test Login Flow

```
1. Logout from CTFd
2. Navigate to /login
3. Should redirect to OAuth provider
4. Complete authentication
5. Should redirect back to CTFd challenges page
6. Check CTFd logs for "Successful OAuth login" message
```

#### 2. Test Logout

```
1. Click logout in CTFd
2. Should be logged out of CTFd
3. If logout URL configured, should also logout from provider
```

#### 3. Test Admin Promotion

```
1. Add test user to admin group in provider
2. Login to CTFd
3. User should have admin privileges
4. Check logs for "promoted to admin via OAuth group" message
```

#### 4. Test Team Mode (if applicable)

```
1. Login with user that has team data
2. Verify team is created or user is added to existing team
3. Check logs for team creation/assignment messages
```

### Rollback Procedure

If you need to rollback:

#### Step 1: Stop CTFd

```bash
docker-compose down
# or
systemctl stop ctfd
```

#### Step 2: Restore Old Plugin

```bash
rm -rf /path/to/CTFd/CTFd/plugins/ctfd-oauth
mv /path/to/CTFd/CTFd/plugins/ctfd-oauth.old /path/to/CTFd/CTFd/plugins/ctfd-oauth
```

#### Step 3: Restore Configuration (if needed)

```bash
# If using SQLite
sqlite3 /path/to/ctfd.db < oauth_config_backup.sql

# If using MySQL/MariaDB
mysql -u user -p ctfd < oauth_config_backup.sql

# If using PostgreSQL
psql -U user ctfd < oauth_config_backup.sql
```

#### Step 4: Start CTFd

```bash
docker-compose up -d
# or
systemctl start ctfd
```

### Getting Help

If you encounter issues:

1. Check the [README.md](README.md) for configuration details
2. Check the [EXAMPLES.md](EXAMPLES.md) for provider-specific configurations
3. Review CTFd logs for detailed error messages
4. Check the [Troubleshooting](README.md#troubleshooting) section
5. Open a GitHub issue with:
   - CTFd version
   - OAuth provider
   - Relevant log messages (redact sensitive data)
   - Steps to reproduce

### Post-Upgrade Recommendations

#### 1. Enable OIDC Discovery

If your provider supports it, switch to OIDC discovery to simplify configuration and ensure endpoints stay up-to-date.

#### 2. Configure Logout URL

Set up proper logout handling to ensure users are logged out from both CTFd and the identity provider.

#### 3. Review Security Settings

- Ensure your CTFd instance uses HTTPS
- Verify redirect URIs are correctly configured in your provider
- Review provider security settings (e.g., token expiration, refresh tokens)

#### 4. Monitor Logs

After upgrade, monitor logs for:
- Successful logins
- Any authentication errors
- Admin promotions
- Team assignments

#### 5. Update Documentation

If you maintain internal documentation, update it to reflect:
- New configuration options
- OIDC discovery support
- Logout URL
- Custom claim mapping

### Version History

#### Version 2.0.0 (2024)

**Security:**
- Added PKCE support
- Enhanced state validation
- Added request timeouts and retries
- Fixed email overwrite vulnerability
- Added comprehensive audit logging

**Features:**
- OIDC discovery support
- Configurable claim mapping
- Configurable scopes
- Logout handler
- Team synchronization
- Configuration validation

**Code Quality:**
- Added type hints
- Refactored large functions
- Improved error messages
- Fixed file handle leak
- Better code organization

#### Version 1.0.0 (Original)

- Basic OAuth 2.0 authentication
- Team mode support
- Admin promotion via groups
