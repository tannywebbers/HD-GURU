from __future__ import annotations

"""Ad provider adapters.

Every provider has a small adapter that knows its integration method and turns
public identifiers (publisher/zone/site ids) into a render descriptor the
frontend can safely mount. New providers can be added here without touching
React components — the admin only configures which providers are enabled.

Security: adapters only ever emit public identifiers. ``api_key`` and other
secrets never reach the frontend. ``custom`` scripts are the explicit
trusted-admin path; the frontend mounts them in an isolated sandboxed frame.
"""

from app.models.ad_provider import AdProvider

#: Registry of known providers -> adapter functions. Unknown names fall back
#: to the provider's configured integration type.
PROVIDER_CATALOG = (
    ("Google AdSense", "script"),
    ("Adsterra", "script"),
    ("PropellerAds", "script"),
    ("Monetag", "script"),
    ("Media.net", "script"),
    ("Ezoic", "script"),
    ("Setupad", "script"),
    ("HilltopAds", "script"),
    ("RevContent", "native"),
    ("Taboola", "native"),
)


def provider_kind(name: str, provider_type: str) -> str:
    """Resolve the client render kind for a provider."""
    if provider_type == "custom":
        return "custom"
    catalog_type = next(
        (t for n, t in PROVIDER_CATALOG if n.lower() == name.lower()), None
    )
    if catalog_type is not None:
        return catalog_type
    return provider_type if provider_type in {"iframe", "script"} else "html"


def _url(text: str | None) -> str:
    return (text or "").strip()


def _ad_script(provider: AdProvider) -> str:
    pub = _url(provider.publisher_id)
    zone = _url(provider.zone_id)
    site = _url(provider.site_id)
    return (
        "<script async src=\"https://pagead2.googlesyndication.com/"
        f"pagead/js/adsbygoogle.js?client={pub}\" crossorigin=\"anonymous\"></script>"
        f"<ins class=\"adsbygoogle\" style=\"display:block\" data-ad-client=\"{pub}\""
        f" data-ad-slot=\"{zone}\" data-ad-format=\"auto\" data-full-width-responsive=\"true\">"
        "</ins>"
        "<script>(adsbygoogle=window.adsbygoogle||[]).push({});</script>"
    )


def _zone_script(provider: AdProvider, host: str) -> str:
    zone = _url(provider.zone_id)
    return (
        f"<script type=\"text/javascript\" src=\"//{host}/{zone}/invoke.js\"></script>"
    )


def _medianet_script(provider: AdProvider) -> str:
    site = _url(provider.site_id) or _url(provider.publisher_id)
    return (
        "<script type=\"text/javascript\">window._mNHandle=window._mNHandle||{};"
        "window._mNHandle.queue=window._mNHandle.queue||[];"
        "medianet_versionId=\"3121199\";</script>"
        f"<script src=\"https://contextual.media.net/nmedianet.js?cid={site}\"></script>"
    )


def _ezoic_script(provider: AdProvider) -> str:
    site = _url(provider.site_id)
    return (
        "<script src=\"https://go.ezoic.net/ezoicfmt.js\"></script>"
        "<script>window.ezstandalone=window.ezstandalone||{};"
        f"ezstandalone.add=ezstandalone.add||function(){{}};ezstandalone.add(\"/{site}\");</script>"
    )


def _setupad_script(provider: AdProvider) -> str:
    pub = _url(provider.publisher_id)
    return f"<script type=\"text/javascript\" src=\"https://cdn.setupad.com/{pub}.js\"></script>"


def _revcontent(provider: AdProvider) -> str:
    zone = _url(provider.zone_id)
    return (
        "<script type=\"text/javascript\" src=\"https://assets.revcontent.com/master.js\"></script>"
        f"<div id=\"revcontent-{zone}\" class=\"rc_p\" data-rc-widget"
        " data-widget-host=\"habitat\" data-endpoint=\"trends.revcontent.com\""
        f" data-widget-id=\"{zone}\"></div>"
    )


def _taboola(provider: AdProvider) -> str:
    pub = _url(provider.publisher_id) or "hdguru"
    placement = _url(provider.zone_id) or "home-thumbnails"
    return (
        "<script type=\"text/javascript\">window._taboola=window._taboola||[];"
        "_taboola.push({article:'auto',url:window.location.href});</script>"
        f"<div id=\"taboola-{placement}\" class=\"trc_related_container\"></div>"
        f"<script>_taboola.push({{mode:'thumbnails-a',container:'taboola-{placement}',"
        f"placement:'{placement}',target_type:'mix'}});</script>"
    )


def _known_adapter(name: str):
    return {
        "google adsense": _ad_script,
        "adsterra": lambda p: _zone_script(p, "www.highperformanceformat.com"),
        "propellerads": lambda p: _zone_script(p, "s4wrdg.com"),
        "monetag": lambda p: _zone_script(p, "tspop.com"),
        "media.net": _medianet_script,
        "ezoic": _ezoic_script,
        "setupad": _setupad_script,
        "hilltopads": lambda p: _zone_script(p, "ukwqnfve.com"),
        "revcontent": _revcontent,
        "taboola": _taboola,
    }.get(name.lower())


def build_render(provider: AdProvider) -> dict:
    """Return the client-safe render descriptor for a provider.

    ``kind`` is one of ``script`` / ``iframe`` / ``html`` / ``custom``.
    For ``iframe`` the descriptor carries a ``src``; the other kinds carry
    ``content`` (markup to mount in the controlled AdSlot component).
    """
    name = provider.name or ""
    kind = provider_kind(name, provider.provider_type or "script")

    if kind == "custom":
        return {"kind": "custom", "content": provider.custom_script or ""}

    if kind == "iframe":
        return {"kind": "iframe", "src": _url(provider.base_url) or ""}

    adapter = _known_adapter(name)
    if adapter is not None:
        try:
            return {"kind": "script", "content": adapter(provider)}
        except Exception:
            pass

    # Generic fallbacks driven by the configured identifiers.
    if kind == "script" or kind == "javascript":
        return {
            "kind": "script",
            "content": provider.custom_script or _zone_script(provider, "cdn.hdguru.app"),
        }
    return {"kind": "html", "content": provider.custom_script or ""}


def validate_provider(provider: AdProvider) -> list[str]:
    """Lightweight config validation; returns a list of missing identifiers."""
    kind = provider_kind(provider.name or "", provider.provider_type or "script")
    missing: list[str] = []
    if kind == "custom" and not (provider.custom_script or "").strip():
        missing.append("custom_script")
    if kind == "iframe" and not (provider.base_url or "").strip():
        missing.append("base_url")
    if kind == "script" or kind == "javascript":
        needs = {"adsense": ("publisher_id", "zone_id")}.get(
            (provider.name or "").lower(), ("zone_id",)
        )
        for field in needs:
            if not getattr(provider, field, None):
                missing.append(field)
    return missing
