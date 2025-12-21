# CTFd OAuth Plugin

A comprehensive OAuth 2.0 / OpenID Connect (OIDC) authentication plugin for CTFd. This plugin replaces CTFd's built-in authentication system with Single Sign-On (SSO) from external identity providers.

## Features

- ✅ **OAuth 2.0 / OIDC Support** - Standards-compliant authentication
- ✅ **Hot Reload** - Enable/disable without restarting CTFd
- ✅ **PKCE Support** - Enhanced security with Proof Key for Code Exchange
- ✅ **OIDC Discovery** - Auto-configure endpoints from discovery URL
- ✅ **Team Mode Support** - Automatic team creation and management
- ✅ **Admin Auto-Promotion** - Grant admin privileges based on group membership
- ✅ **Configurable Claim Mapping** - Map non-standard claim names
- ✅ **Session Management** - Proper logout handling with provider
- ✅ **Comprehensive Logging** - Audit trail for all authentication events
- ✅ **Security Hardened** - Request timeouts, retry logic, state validation
- ✅ **Performance Optimized** - Cached configuration checks

## Installation

1. Copy this plugin directory to your CTFd plugins folder:
   ```bash
   cp -r ctfd-oauth /path/to/CTFd/CTFd/plugins/
   ```

2. Restart CTFd:
   ```bash
   docker-compose restart  # or your deployment method
   ```

3. Navigate to `/admin/oauth2` in your CTFd instance to configure the plugin.

**Note:** Configuration changes take effect immediately without requiring a restart!

## Configuration

### Quick Start with OIDC Discovery (Recommended)

1. Navigate to **Admin Panel > OAuth Configuration**
2. Enter your OIDC discovery URL (e.g., `https://idp.example.com/.well-known/openid-configuration`)
3. Enter your **Client ID** and **Client Secret**
4. Click **Save Configuration** - endpoints will be auto-discovered
5. Set **Plugin Status** to **Enabled**
6. Click **Save Configuration** again

### Manual Configuration

If your identity provider doesn't support OIDC discovery:

1. Navigate to **Admin Panel > OAuth Configuration**
2. Enter the following:
   - **Client ID** - From your OAuth provider
   - **Client Secret** - From your OAuth provider
   - **Authorization Endpoint** - Where users login
   - **Token Endpoint** - Token exchange endpoint
   - **UserInfo Endpoint** - User profile endpoint
   - **Profile URL** (optional) - External profile management URL
   - **Logout URL** (optional) - Provider logout endpoint
3. Set **Plugin Status** to **Enabled**
4. Click **Save Configuration**

## Provider Examples

### Authentik

**OIDC Discovery URL:**
```
https://authentik.example.com/application/o/ctfd/.well-known/openid-configuration
```

**Scopes:** `openid profile email`

**Required Claims:**
- `preferred_username` or `username`
- `email`
- `groups` (for admin promotion)

**Authentik Application Configuration:**
- Client Type: Confidential
- Authorization Flow: Authorization Code with PKCE
- Redirect URIs: `https://ctfd.example.com/oauth2/callback`

### Keycloak

**OIDC Discovery URL:**
```
https://keycloak.example.com/realms/{realm-name}/.well-known/openid-configuration
```

**Scopes:** `openid profile email`

**Required Claims:**
- `preferred_username`
- `email`
- `groups` (for admin promotion)

**Keycloak Client Configuration:**
- Client Protocol: openid-connect
- Access Type: confidential
- Valid Redirect URIs: `https://ctfd.example.com/oauth2/callback`
- Enable PKCE

### Auth0

**OIDC Discovery URL:**
```
https://{tenant}.auth0.com/.well-known/openid-configuration
```

**Scopes:** `openid profile email`

**Auth0 Application Configuration:**
- Application Type: Regular Web Application
- Allowed Callback URLs: `https://ctfd.example.com/oauth2/callback`
- Advanced Settings > OAuth > PKCE: Enabled

### Okta

**OIDC Discovery URL:**
```
https://{org}.okta.com/.well-known/openid-configuration
```

**Scopes:** `openid profile email`

**Okta Application Configuration:**
- Application Type: Web
- Grant Type: Authorization Code
- Sign-in redirect URIs: `https://ctfd.example.com/oauth2/callback`

## Advanced Configuration

### Custom Claim Mapping

If your identity provider uses non-standard claim names, configure them in the **Advanced** tab:

```
Username Claim: sub          # Instead of preferred_username
Email Claim: mail            # Instead of email
Affiliation Claim: org       # Instead of affiliation
```

### Custom OAuth Scopes

Override default scopes in the **Advanced** tab:

```
OAuth Scope: openid profile email groups roles
```

### Admin Group Configuration

Configure which group grants admin privileges:

```
Admin Group Name: CTFd Administrators
```

Users with this group in their `groups` claim will automatically become CTFd admins.

### Team Synchronization

Enable **Sync Team Membership** in the **Advanced** tab to automatically update team assignments on each login.

## Team Mode

When CTFd is in team mode, the plugin expects the userinfo endpoint to return a `team` object:

```json
{
  "preferred_username": "john.doe",
  "email": "john@example.com",
  "team": {
    "id": "team-123",
    "name": "Team Awesome"
  }
}
```

Teams are automatically created and users are assigned based on this data.

## Hot Reload

The plugin supports dynamic enable/disable without requiring CTFd restart:

- **How it works:** Route handlers dynamically check the OAuth configuration on each request
- **Performance:** Configuration status is cached for 60 seconds to minimize database queries
- **Cache invalidation:** Cache is automatically cleared when you save configuration changes
- **Instant activation:** When you enable OAuth and save, it becomes active immediately
- **Safe disable:** When you disable OAuth and save, users can immediately use normal CTFd login

This means you can:
- Test OAuth configuration without downtime
- Quickly disable OAuth if issues occur
- Switch between OAuth and normal authentication on the fly

## Security Features

### PKCE (Proof Key for Code Exchange)

The plugin implements PKCE (RFC 7636) for enhanced security. This protects against authorization code interception attacks.

### State Parameter Validation

CSRF protection through cryptographically secure state parameters using constant-time comparison.

### Request Timeouts & Retries

- Default timeout: 10 seconds
- Automatic retries on transient failures (500, 502, 504)
- Prevents hung connections and DoS

### Secure Session Management

- OAuth state stored in server-side sessions
- PKCE code verifier secured in session
- Automatic cleanup of session data after use

### Comprehensive Logging

All authentication events are logged:
- Successful logins
- Failed authentication attempts
- Admin promotions
- Team assignments
- Configuration errors

## Troubleshooting

### Error: "OAuth Settings not configured"

**Solution:** Ensure you've entered at least Client ID and either Discovery URL or all manual endpoints.

### Error: "OAuth state validation failed"

**Cause:** CSRF token mismatch or session expired.

**Solution:**
- Ensure cookies are enabled
- Check session configuration in CTFd
- Verify redirect URI matches exactly in provider config

### Error: "Failed to obtain access token"

**Possible Causes:**
1. Invalid client credentials
2. Redirect URI mismatch
3. PKCE not supported by provider

**Solution:**
- Verify client ID/secret are correct
- Check provider logs for detailed error
- Ensure redirect URI in provider matches: `https://your-ctfd.com/oauth2/callback`

### Error: "Failed to retrieve user information"

**Cause:** Userinfo endpoint unreachable or returned invalid data.

**Solution:**
- Test userinfo endpoint manually with a valid token
- Check required claims are present
- Review claim mapping configuration

### Users Not Becoming Admins

**Solution:**
- Verify the admin group name matches exactly (case-sensitive)
- Ensure users have the group in their `groups` claim
- Check CTFd logs for admin promotion messages

### Team Mode Not Working

**Solution:**
- Ensure CTFd is in team mode
- Verify userinfo returns `team` object with `id` and `name`
- Check logs for team creation messages

## Plugin Structure

```
ctfd-oauth/
├── __init__.py           # Plugin loader and initialization
├── auth.py               # OAuth authentication flow
├── blueprint.py          # Flask routes
├── models.py             # Database models
├── db_utils.py           # Database utilities and validation
├── config.json           # Plugin metadata
├── templates/
│   └── oauth2/
│       └── config.html   # Admin configuration UI
└── README.md             # This file
```

## Configuration Schema

All configuration is stored in the `OAUTHConfig` database table:

| Key | Description | Required |
|-----|-------------|----------|
| `oauth_plugin_enabled` | Enable/disable plugin | Yes |
| `oauth_client_id` | OAuth client identifier | Yes |
| `oauth_client_secret` | OAuth client secret | Yes |
| `oauth_discovery_url` | OIDC discovery URL | No* |
| `oauth_authorization_endpoint` | Authorization URL | No* |
| `oauth_token_endpoint` | Token exchange URL | No* |
| `oauth_userinfo_url` | UserInfo URL | No* |
| `oauth_profile_url` | External profile URL | No |
| `oauth_logout_url` | Provider logout URL | No |
| `oauth_scope` | OAuth scopes | No |
| `oauth_admin_group` | Admin group name | No |
| `oauth_sync_teams` | Sync teams on login | No |
| `oauth_claim_preferred_username` | Username claim mapping | No |
| `oauth_claim_email` | Email claim mapping | No |
| `oauth_claim_affiliation` | Affiliation claim mapping | No |

\* Either `oauth_discovery_url` OR all three manual endpoints are required.

## Development

### Running Tests

```bash
# TODO: Add test suite
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Security Considerations

### Client Secret Storage

Client secrets are currently stored in plaintext in the database. For production deployments, consider:
- Database encryption at rest
- Environment variable configuration
- Secret management systems (Vault, AWS Secrets Manager, etc.)

### HTTPS Requirement

This plugin should **only** be used over HTTPS in production. OAuth flows over HTTP are vulnerable to token interception.

### Redirect URI Validation

Ensure your identity provider strictly validates redirect URIs. The callback URL must be:
```
https://your-ctfd-domain.com/oauth2/callback
```

## License

This plugin is distributed under the same license as CTFd.

## Support

For issues and questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review CTFd logs for detailed error messages
3. Consult your identity provider's documentation
4. Open an issue on GitHub

## Changelog

### Version 2.0.0 (Current)

**Security Improvements:**
- ✅ Added PKCE support
- ✅ Improved state validation with constant-time comparison
- ✅ Added request timeouts and retry logic
- ✅ Enhanced JSON response validation
- ✅ Fixed email overwrite vulnerability
- ✅ URL parameter encoding
- ✅ Comprehensive audit logging

**Features:**
- ✅ OIDC discovery support
- ✅ Configurable claim mapping
- ✅ Configurable scopes
- ✅ Logout handler with provider logout
- ✅ Team synchronization option
- ✅ Configuration validation
- ✅ Better error messages

**Code Quality:**
- ✅ Added type hints throughout
- ✅ Refactored large functions
- ✅ Removed magic strings
- ✅ Fixed file handle leak
- ✅ Removed unused imports
- ✅ Improved code organization

**UX Improvements:**
- ✅ Password input for client secret
- ✅ Show/hide secret toggle
- ✅ Comprehensive help text
- ✅ Better form organization
- ✅ Advanced settings tab
- ✅ Success/error notifications

### Version 1.0.0 (Original)

- Basic OAuth 2.0 authentication
- Team mode support
- Admin promotion via groups
