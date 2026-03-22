import frappe
from frappe import _


# ── Auth ──────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=False)
def get_logged_user() -> str:
    """
    Returns the currently logged-in user's email.
    Used by Next.js middleware to verify the `sid` cookie server-side.

    Next.js calls: GET /api/method/frappe_next_bridge.api.get_logged_user
    with Cookie: sid=<value>
    """
    return frappe.session.user


@frappe.whitelist(allow_guest=True)
def get_boot_info() -> dict:
    """
    Returns minimal boot data for Next.js Server Components.
    Includes CSRF token, site name, and logged-in user.

    Calling this from Next.js layout.tsx is optional — the SDK's
    getFrappeBootData() reads x-frappe-user from middleware headers instead.
    """
    return {
        "user":           frappe.session.user,
        "csrf_token":     frappe.sessions.get_csrf_token(),
        "site_name":      frappe.local.site,
        "frappe_version": frappe.__version__,
        "is_guest":       frappe.session.user == "Guest",
    }


# ── Health ────────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def health() -> dict:
    """
    Simple health-check endpoint.
    Used by Docker Compose healthcheck and dev.sh startup validation.

    GET /api/method/frappe_next_bridge.api.health
    """
    return {"status": "ok", "site": frappe.local.site}
