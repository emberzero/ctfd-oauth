# OAuth Provider Configuration Examples

This document provides detailed configuration examples for popular OAuth/OIDC providers.

## Table of Contents

- [Authentik](#authentik)
- [Keycloak](#keycloak)
- [Auth0](#auth0)
- [Okta](#okta)
- [Azure AD / Entra ID](#azure-ad--entra-id)
- [Google](#google)
- [GitHub](#github)
- [GitLab](#gitlab)

---

## Authentik

### Provider Setup

1. Navigate to **Applications > Providers**
2. Click **Create**
3. Select **OAuth2/OpenID Provider**
4. Configure:
   - **Name:** CTFd
   - **Client Type:** Confidential
   - **Client ID:** (auto-generated)
   - **Client Secret:** (auto-generated)
   - **Redirect URIs/Origins:** `https://your-ctfd.com/oauth2/callback`
   - **Signing Key:** Select or create a key
   - **Scopes:** `openid`, `profile`, `email`, `groups`

5. Navigate to **Applications > Applications**
6. Click **Create**
7. Configure:
   - **Name:** CTFd
   - **Slug:** `ctfd`
   - **Provider:** Select the provider created above

### CTFd Plugin Configuration

**Using OIDC Discovery (Recommended):**
```
Discovery URL: https://authentik.company.com/application/o/ctfd/.well-known/openid-configuration
Client ID: <from Authentik>
Client Secret: <from Authentik>
```

**Manual Configuration:**
```
Client ID: <from Authentik>
Client Secret: <from Authentik>
Authorization Endpoint: https://authentik.company.com/application/o/authorize/
Token Endpoint: https://authentik.company.com/application/o/token/
UserInfo URL: https://authentik.company.com/application/o/userinfo/
Profile URL: https://authentik.company.com/if/user/
Logout URL: https://authentik.company.com/application/o/ctfd/end-session/
```

### Group-Based Admin Access

1. In Authentik, create a group named "CTFd Admins"
2. Add users to this group
3. In CTFd OAuth config (Advanced tab):
   ```
   Admin Group Name: CTFd Admins
   ```

### Team Mode Configuration

For team mode, create a custom property mapper in Authentik:

1. Navigate to **Customization > Property Mappings**
2. Click **Create > Scope Mapping**
3. Configure:
   - **Name:** Team Mapping
   - **Scope name:** `team`
   - **Expression:**
     ```python
     return {
         "team": {
             "id": request.user.team_id,
             "name": request.user.team_name
         }
     }
     ```
4. Attach this mapping to your OAuth provider

---

## Keycloak

### Realm and Client Setup

1. Create or select a realm
2. Navigate to **Clients > Create**
3. Configure:
   - **Client ID:** `ctfd`
   - **Client Protocol:** `openid-connect`
   - **Root URL:** `https://your-ctfd.com`

4. In the client settings:
   - **Access Type:** `confidential`
   - **Valid Redirect URIs:** `https://your-ctfd.com/oauth2/callback`
   - **Web Origins:** `https://your-ctfd.com`
   - **Enable PKCE:** `On`

5. Go to **Credentials** tab and copy the **Secret**

### CTFd Plugin Configuration

**Using OIDC Discovery (Recommended):**
```
Discovery URL: https://keycloak.company.com/realms/master/.well-known/openid-configuration
Client ID: ctfd
Client Secret: <from Keycloak Credentials tab>
```

**Manual Configuration:**
```
Client ID: ctfd
Client Secret: <from Keycloak>
Authorization Endpoint: https://keycloak.company.com/realms/master/protocol/openid-connect/auth
Token Endpoint: https://keycloak.company.com/realms/master/protocol/openid-connect/token
UserInfo URL: https://keycloak.company.com/realms/master/protocol/openid-connect/userinfo
Logout URL: https://keycloak.company.com/realms/master/protocol/openid-connect/logout
```

### Group Mapper

1. Navigate to **Clients > ctfd > Mappers**
2. Click **Create**
3. Configure:
   - **Name:** `groups`
   - **Mapper Type:** `Group Membership`
   - **Token Claim Name:** `groups`
   - **Full group path:** `Off`
   - **Add to ID token:** `On`
   - **Add to access token:** `On`
   - **Add to userinfo:** `On`

### Admin Group

1. Create a group "CTFd Admins" in Keycloak
2. In CTFd OAuth config:
   ```
   Admin Group Name: CTFd Admins
   ```

---

## Auth0

### Application Setup

1. Navigate to **Applications > Applications**
2. Click **Create Application**
3. Configure:
   - **Name:** CTFd
   - **Application Type:** Regular Web Application
   - **Technology:** Choose any (doesn't matter)

4. In Application Settings:
   - **Allowed Callback URLs:** `https://your-ctfd.com/oauth2/callback`
   - **Allowed Logout URLs:** `https://your-ctfd.com`
   - **Allowed Web Origins:** `https://your-ctfd.com`

5. In **Advanced Settings > OAuth**:
   - **JsonWebToken Signature Algorithm:** RS256
   - **OIDC Conformant:** Enabled

6. Copy **Domain**, **Client ID**, and **Client Secret**

### CTFd Plugin Configuration

**Using OIDC Discovery:**
```
Discovery URL: https://YOUR_DOMAIN.auth0.com/.well-known/openid-configuration
Client ID: <from Auth0>
Client Secret: <from Auth0>
```

### Adding Groups to Tokens

Create an Auth0 Rule to add groups:

1. Navigate to **Auth Pipeline > Rules**
2. Create a new rule:
```javascript
function addGroupsToToken(user, context, callback) {
  const namespace = 'https://ctfd.com/';
  context.idToken[namespace + 'groups'] = user.app_metadata.groups || [];
  context.accessToken[namespace + 'groups'] = user.app_metadata.groups || [];
  callback(null, user, context);
}
```

3. In CTFd OAuth config (Advanced):
```
Admin Group Name: CTFd Admins
```

4. Add groups to users via **User Management > Users > {user} > app_metadata**:
```json
{
  "groups": ["CTFd Admins"]
}
```

---

## Okta

### Application Setup

1. Navigate to **Applications > Applications**
2. Click **Create App Integration**
3. Configure:
   - **Sign-in method:** OIDC
   - **Application type:** Web Application
   - **App integration name:** CTFd

4. Configure:
   - **Sign-in redirect URIs:** `https://your-ctfd.com/oauth2/callback`
   - **Sign-out redirect URIs:** `https://your-ctfd.com`
   - **Controlled access:** Choose appropriate option

5. Copy **Client ID** and **Client secret**

### CTFd Plugin Configuration

**Using OIDC Discovery:**
```
Discovery URL: https://your-org.okta.com/.well-known/openid-configuration
Client ID: <from Okta>
Client Secret: <from Okta>
```

### Group Claims

1. Navigate to **Security > API > Authorization Servers**
2. Select your authorization server (default)
3. Go to **Claims** tab
4. Click **Add Claim**:
   - **Name:** `groups`
   - **Include in token type:** ID Token, Always
   - **Value type:** Groups
   - **Filter:** Regex: `.*`
   - **Include in:** `The following scopes:` profile

---

## Azure AD / Entra ID

### App Registration

1. Navigate to **Azure Active Directory > App registrations**
2. Click **New registration**
3. Configure:
   - **Name:** CTFd
   - **Supported account types:** Accounts in this organizational directory only
   - **Redirect URI:** Web - `https://your-ctfd.com/oauth2/callback`

4. After creation:
   - Copy **Application (client) ID**
   - Copy **Directory (tenant) ID**

5. Navigate to **Certificates & secrets**
6. Click **New client secret**
7. Copy the secret value immediately (shown only once)

### CTFd Plugin Configuration

**Using OIDC Discovery:**
```
Discovery URL: https://login.microsoftonline.com/{tenant-id}/v2.0/.well-known/openid-configuration
Client ID: <Application ID>
Client Secret: <Client Secret>
```

**Manual Configuration:**
```
Client ID: <Application ID>
Client Secret: <Client Secret>
Authorization Endpoint: https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/authorize
Token Endpoint: https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token
UserInfo URL: https://graph.microsoft.com/oidc/userinfo
Logout URL: https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/logout
Scope: openid profile email
```

### Claim Mapping

Azure AD uses different claim names:

**In CTFd OAuth config (Advanced):**
```
Username Claim: preferred_username
Email Claim: email
```

### Group Claims

1. In App registration, navigate to **Token configuration**
2. Click **Add groups claim**
3. Select **Security groups**

---

## Google

### OAuth Client Setup

1. Navigate to [Google Cloud Console](https://console.cloud.google.com)
2. Create or select a project
3. Navigate to **APIs & Services > Credentials**
4. Click **Create Credentials > OAuth client ID**
5. Configure:
   - **Application type:** Web application
   - **Name:** CTFd
   - **Authorized redirect URIs:** `https://your-ctfd.com/oauth2/callback`

6. Copy **Client ID** and **Client secret**

### CTFd Plugin Configuration

**Using OIDC Discovery:**
```
Discovery URL: https://accounts.google.com/.well-known/openid-configuration
Client ID: <from Google>
Client Secret: <from Google>
Scope: openid profile email
```

### Notes

- Google doesn't provide a groups claim by default
- Admin promotion won't work unless you set up Google Workspace with custom attributes
- Best suited for individual (non-team) CTF mode

---

## GitHub

**Note:** GitHub uses OAuth 2.0 but not OIDC, requiring custom implementation.

### OAuth App Setup

1. Navigate to **Settings > Developer settings > OAuth Apps**
2. Click **New OAuth App**
3. Configure:
   - **Application name:** CTFd
   - **Homepage URL:** `https://your-ctfd.com`
   - **Authorization callback URL:** `https://your-ctfd.com/oauth2/callback`

4. Copy **Client ID** and **Client Secret**

### CTFd Plugin Configuration

**Manual Configuration:**
```
Client ID: <from GitHub>
Client Secret: <from GitHub>
Authorization Endpoint: https://github.com/login/oauth/authorize
Token Endpoint: https://github.com/login/oauth/access_token
UserInfo URL: https://api.github.com/user
Scope: read:user user:email
```

**Claim Mapping (Advanced):**
```
Username Claim: login
Email Claim: email
```

### Limitations

- No standard groups claim
- Email may not be public (requires user:email scope)
- Admin promotion requires custom GitHub app with organization membership

---

## GitLab

### Application Setup

1. Navigate to **Admin Area > Applications** (self-hosted) or **User Settings > Applications** (GitLab.com)
2. Click **New application**
3. Configure:
   - **Name:** CTFd
   - **Redirect URI:** `https://your-ctfd.com/oauth2/callback`
   - **Scopes:** `openid`, `profile`, `email`

4. Copy **Application ID** and **Secret**

### CTFd Plugin Configuration

**Using OIDC Discovery:**
```
Discovery URL: https://gitlab.com/.well-known/openid-configuration
Client ID: <Application ID>
Client Secret: <Secret>
```

**For Self-Hosted GitLab:**
```
Discovery URL: https://gitlab.company.com/.well-known/openid-configuration
Client ID: <Application ID>
Client Secret: <Secret>
```

### Notes

- GitLab provides groups in the `groups` claim automatically
- Works well with both individual and team modes

---

## Testing Your Configuration

After configuring any provider:

1. **Test OIDC Discovery:**
   - Visit the discovery URL in a browser
   - Verify it returns a JSON document with endpoints

2. **Test Login Flow:**
   - Log out of CTFd
   - Visit `/login` (should redirect to provider)
   - Complete authentication
   - Verify successful login and redirect to challenges

3. **Check Logs:**
   - Review CTFd logs for any errors
   - Look for successful login messages

4. **Test Logout:**
   - Click logout
   - Verify logout from CTFd
   - If logout URL configured, verify logout from provider

5. **Test Admin Promotion:**
   - Add a test user to admin group in provider
   - Login to CTFd
   - Verify admin access granted

## Common Issues

### Redirect URI Mismatch

**Error:** `redirect_uri_mismatch`

**Solution:** Ensure the redirect URI in your provider exactly matches:
```
https://your-ctfd.com/oauth2/callback
```
- Check for trailing slashes
- Verify HTTP vs HTTPS
- Ensure domain matches exactly

### Missing Claims

**Error:** "OAuth userinfo missing required fields"

**Solution:**
- Verify scopes include `profile` and `email`
- Check claim mapping in Advanced settings
- Test userinfo endpoint with a token

### PKCE Not Supported

Some older providers don't support PKCE. The plugin will still work, but PKCE parameters will be ignored by the provider.

### CORS Errors

OAuth flows should not trigger CORS errors. If you see CORS issues:
- Verify you're using server-side flow (not implicit)
- Check redirect URIs are configured correctly
- Ensure you're not making client-side API calls
