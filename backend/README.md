# BMW PHP License Server — Step 3

A standalone **PHP 8.2+ / MySQL 8.0** licensing backend implementing the request/response contract statically recovered from BMW Python 3.11 `license_client.pyc`.

**The BMW EXE is not modified here.** This does not restore PyArmor-protected `bmw_gui.pyc` or prove that the legacy compiled app can be pointed to this backend.

## Verified API

`POST /api/app/fauth/license/check`

```http
Content-Type: application/json
```

```json
{"Key":"YOUR-LICENSE-KEY","Machine":"YOUR-DEVICE-ID"}
```

Alternative route also supported: `POST /api/v1/license/validate`, which accepts the same fields or `{"licenseKey":"...","deviceId":"..."}`.

Valid response, HTTP 200:

```json
{"success":true,"leftDays":30,"message":"License OK.","KeyType":"standard","paid":true,"UpdateURL":""}
```

Invalid or expired license: HTTP 401, `{"success":false,"message":"..."}`.

Device limit reached: HTTP 409. Rate limit: HTTP 429.

Health endpoint: `GET /health`.

No separate GET license endpoint has been confirmed in the recovered Python licensing client.

## cPanel Installation

1. Use a PHP 8.2+ hosting account with `pdo_mysql`, HTTPS and Apache with `mod_rewrite` / `.htaccess` support.
2. From the GitHub Actions **BMW-PHP-LICENSE-SERVER-PACKAGE** artifact, download ZIP and extract the **contents** of the `backend/` directory to your selected document root, such as a dedicated subdomain's `public_html`.
3. In cPanel MySQL Database Wizard, create a **new empty MySQL database** and a user with its full required database privileges.
4. Browse to `https://YOUR-DOMAIN/install.php`, enter MySQL host, database/user/password and choose your Admin email/password (minimum 12 characters). Installer automatically creates schema and its first administrator. **Do not manually import `schema.mysql.sql` first unless you know what you are doing.**
5. Sign in at `https://YOUR-DOMAIN/admin.php`. Use **Create / Import License** to enter your **existing BMW license key**, a label, expiry days, plan, and maximum devices. Key value is entered through the private admin form; **do not commit license keys to GitHub**.
6. Test with your own network client before integrating into a BMW Windows app:

```bash
curl -X POST 'https://YOUR-DOMAIN/api/app/fauth/license/check' \
  -H 'Content-Type: application/json' \
  -d '{"Key":"YOUR-LICENSE-KEY","Machine":"YOUR-DEVICE-ID"}'
```

7. Confirm in AdminLTE dashboard you can revoke the license, then verify the API rejects that same key with HTTP 401. Restore status only if intended.
8. After setup, `install.php` auto-disables via the generated `storage/config.php`. Prefer removing or renaming `install.php` on production after successful setup.

### Important upload layout

Correct:
```text
public_html/
  .htaccess
  admin.php
  api.php
  install.php
  router.php
  schema.mysql.sql
  app/
  storage/
```

Incorrect: `public_html/backend/admin.php` if you intend URLs directly at the domain root.

The MySQL schema file, `storage/`, and `app/` are blocked by Apache `.htaccess`. If using Nginx, add equivalent server rules before deployment; do not expose internal files or secrets.

## Key and device behavior

- License key: case-insensitive, trimmed, `A-Z`, digits and hyphen, 8–128 characters.
- License key is stored as SHA-256 hash; admin displays only a short key hint.
- Device identity is stored hashed for binding. For one-device keys, the first valid request binds the first machine.
- Additional machines are rejected once the bound device limit is reached.
- Reset Devices explicitly removes all bindings for a license.
- Revoked or suspended licenses are rejected.
- Expiry checked at each validation.
- CSRF protection and PHP session login apply to Admin actions.
- Rate limiting uses request attempts by connecting IP.

## Tests and evidence

GitHub CI: `.github/workflows/bmw-php-mysql-ci.yml`

Uses PHP 8.2 / MySQL 8.0, PHP syntax lint, and HTTP tests:
installer, config lock, admin login, license import, activation, repeated validation,
device limit, invalid key rejection, alternate payload, revoke and rejection.

The CI tests use a dummy license key only, not a customer's actual key.

## Remaining BMW work

- Step 2: Original `bmw_gui.pyc` application is PyArmor-protected. The reconstructed client and dialog exist on `recovery/bmw-static-20261113`, but they are not integrated into that original GUI.
- Step 3: Backend implementation and PHP/MySQL CI tests are complete. Deployment to your cPanel account and real BMW client integration remain untested.
- Step 4: A functioning recompiled BMW.exe has **not** been produced; do not claim compatibility with the compiled legacy app.

## Server URL configuration

The editable Python recovered client accepts `LICENSE_API_URL`. To avoid switching the request field names unexpectedly, use a URL containing `/fauth` for a server that expects `Key/Machine`. The new backend accepts both field sets.

This does not prove that changing `LICENSE_API_URL` alone switches the existing compiled BMW.exe; its PyArmor-protected entry point could override the parameter.
