app_name    = "frappe_next_bridge"
app_title   = "Frappe Next Bridge"
app_publisher = "Your Name"
app_description = "Frappe companion app for the frappe-next-bridge monorepo"
app_email   = "you@example.com"
app_license = "MIT"

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow Next.js dev server to call Frappe API directly.
# In Docker production: Nginx handles routing, CORS not needed.
# In local dev: Next.js at :3000 calls Frappe at :8000 → needs CORS.
allow_cors = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# ── Login page custom skin ────────────────────────────────────────────────────
# Injected into every web/portal page (web.html).
# CSS is scoped to body:has(.for-login) so it only affects /login.
web_include_css = "/assets/frappe_next_bridge/css/login.css"
web_include_js  = "/assets/frappe_next_bridge/js/login.js"

# ── Optional: expose Next.js as Frappe website page ───────────────────────────
# Uncomment if you want Frappe to hand off certain routes to Next.js.
# website_route_rules = [
#     {"from_route": "/next/<path:app_path>", "to_route": "next_bridge"},
# ]
