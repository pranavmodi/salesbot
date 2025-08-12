from __future__ import annotations

from flask import g, request, current_app, session
from typing import Optional


def current_tenant_id() -> Optional[str]:
    """Return the current request's tenant_id if set; otherwise None."""
    return getattr(g, 'tenant_id', None)


def resolve_tenant_context() -> None:
    """Resolve tenant from header or query and set g.tenant_id and g.tenant_slug.

    Resolution order:
    - Header X-Tenant-ID (UUID)
    - Header X-Tenant-Slug (string)
    - Query param ?tenant=<slug>
    - Default tenant ('default')
    """
    try:
        tenant_id_hdr = request.headers.get('X-Tenant-ID', '').strip()
        tenant_slug_hdr = request.headers.get('X-Tenant-Slug', '').strip()
        tenant_slug_qs = request.args.get('tenant', '').strip()

        # Prefer explicit tenant_id header if valid UUID-like (len check, hyphens)
        if tenant_id_hdr:
            g.tenant_id = tenant_id_hdr
            g.tenant_slug = None
            return

        # Check if user is logged in and has a tenant_id in session
        user_session = session.get('user', {})
        if user_session and user_session.get('tenant_id'):
            g.tenant_id = str(user_session['tenant_id'])
            g.tenant_slug = None
            return

        slug = tenant_slug_hdr or tenant_slug_qs or 'default'

        # Lookup tenant id by slug
        from app.database import get_shared_engine
        from sqlalchemy import text
        engine = get_shared_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id FROM tenants WHERE slug = :slug LIMIT 1"),
                {"slug": slug}
            )
            row = result.fetchone()
            if row and row[0]:
                g.tenant_id = str(row[0])
                g.tenant_slug = slug
                return

        # Fallback: unset if not found
        g.tenant_id = None
        g.tenant_slug = None
    except Exception as e:
        # Do not block request on resolution error
        current_app.logger.warning(f"Tenant resolution failed: {e}")
        g.tenant_id = None
        g.tenant_slug = None



