#!/usr/bin/env python3
"""Rebuild Island PT pages on the Distinct Designs layout system.

Reads HTML from git `main` (the live-site source) and writes this branch's
pages. Safe to re-run. Does not change main.

    python3 generate_variation.py
"""

from __future__ import annotations

import html
import posixpath
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
PHONE_DISPLAY = "(808) 201-6922"
PHONE_TEL = "tel:8082016922"
PHONE_SMS = "sms:+18082016922"
EMAIL = "Teddy@islandPTmaui.com"
BOOK = "/booking"
GOOGLE = "https://www.google.com/maps?cid=11638500063304272".replace(
    "11638500063304272", "11638500063304212272"
)
CRED = "https://www.credential.net/b6594d97-3d1e-4cb2-a8fe-9042d0001795"
BADGE = "https://api.accredible.com/v1/frontend/credential_website_embed_image/badge/188134442"

# Photographic heroes when the source hero is a CSS background, not an <img>.
HERO_IMAGE = {
    "index.html": (
        "/img/outrigger-canoe-race-maui.webp",
        "Outrigger canoe crew racing through open ocean swell off Maui",
    ),
}

PAGES = [
    "index.html",
    "about.html",
    "services.html",
    "mobile-physical-therapy.html",
    "service-area.html",
    "why-cash-pay.html",
    "testimonials.html",
    "contact.html",
    "privacy-policy.html",
    "terms.html",
    "thank-you.html",
    "physical-therapy-kahului.html",
    "physical-therapy-kihei.html",
    "physical-therapy-kula.html",
    "physical-therapy-makawao.html",
    "physical-therapy-makena.html",
    "physical-therapy-wailea.html",
    "blog/index.html",
    "blog/low-back-pain/index.html",
    "blog/peptides-recovery/index.html",
]

NAV = [
    ("Home", "/"),
    (
        "About Us",
        [
            ("About", "/about.html"),
            ("Blog", "/blog"),
            ("Why Cash-Pay", "/why-cash-pay.html"),
        ],
    ),
    (
        "Services",
        [
            ("Services Overview", "/services.html"),
            ("Mobile Physical Therapy", "/mobile-physical-therapy.html"),
        ],
    ),
    (
        "Service Area",
        [
            ("Service Area Overview", "/service-area.html"),
            ("Kīhei", "/physical-therapy-kihei.html"),
            ("Wailea", "/physical-therapy-wailea.html"),
            ("Mākena", "/physical-therapy-makena.html"),
            ("Kahului", "/physical-therapy-kahului.html"),
            ("Kula", "/physical-therapy-kula.html"),
            ("Makawao", "/physical-therapy-makawao.html"),
        ],
    ),
    ("Reviews", "/testimonials.html"),
    ("Contact", "/contact.html"),
]


class Node:
    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children = []

    def cls(self):
        return self.attrs.get("class", "")

    def has_class(self, name):
        return name in self.cls().split()


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
            return
        if self.skip:
            return
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in ("img", "br", "hr", "wbr", "input", "source", "meta", "link"):
            self.stack.append(node)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            if self.skip:
                self.skip -= 1
            return
        if self.skip:
            return
        if tag in ("img", "br", "hr", "wbr", "input", "source", "meta", "link"):
            return
        # Pop back to the matching tag if the source is slightly uneven.
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.skip or not data:
            return
        self.stack[-1].children.append(data)

    def handle_comment(self, data):
        if self.skip:
            return
        if "HIDDEN" in data or "TODO" in data:
            self.stack[-1].children.append(Node("comment", {"data": data}))


def git_show(path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"main:{path}"], cwd=ROOT, text=True, errors="replace"
    )


def parse(doc: str) -> Node:
    p = Parser()
    p.feed(doc)
    p.close()
    return p.root


def find_all(node, tag):
    out = []
    if isinstance(node, Node) and node.tag == tag:
        out.append(node)
    if isinstance(node, Node):
        for c in node.children:
            out.extend(find_all(c, tag))
    return out


def find_first(node, tag):
    found = find_all(node, tag)
    return found[0] if found else None


def text_of(node) -> str:
    if isinstance(node, str):
        return node
    if node.tag in ("script", "style", "svg"):
        return ""
    return "".join(text_of(c) for c in node.children)


def attr_esc(value: str) -> str:
    return html.escape(value, quote=True)


def abs_url(url: str, source: str) -> str:
    if not url:
        return url
    lower = url.lower()
    if lower.startswith(("http://", "https://", "mailto:", "tel:", "sms:", "#", "data:")):
        return url
    if url.startswith("/"):
        return url
    base = posixpath.dirname(source)
    joined = posixpath.normpath(posixpath.join(base, url))
    return "/" + joined.lstrip("/")


_faq_n = 0
SKIP = set()


def next_faq_id() -> str:
    global _faq_n
    _faq_n += 1
    return f"faq-{_faq_n}"


def is_booking(href: str) -> bool:
    return bool(href) and ("/booking" in href or "janeapp.com" in href)


def class_has(node: Node, *names) -> bool:
    parts = set(node.cls().split())
    return any(n in parts for n in names)


def is_step(node) -> bool:
    return isinstance(node, Node) and class_has(node, "phase", "kokua-step", "step")


def is_quote(node) -> bool:
    return isinstance(node, Node) and class_has(node, "t-card", "tm-card")


def is_spread(node) -> bool:
    return isinstance(node, Node) and node.tag == "article" and class_has(node, "spread-row")


def is_service_card_article(node) -> bool:
    return isinstance(node, Node) and node.tag == "article" and class_has(
        node, "specialty", "service-card"
    )


INLINE_KEEP = {"a", "strong", "b", "em", "i", "br", "wbr"}
BLOCK_KEEP = {"p", "ul", "ol", "li", "h3", "h4", "blockquote", "figure", "img", "figcaption"}


def glue(parts) -> str:
    """Keep a space between adjacent inline runs so dates and labels do not collide."""
    out = []
    for part in parts:
        if not part:
            continue
        if out:
            prev = out[-1]
            if prev[-1].isalnum() and part[0].isalnum():
                out.append(" ")
            elif prev.endswith(">") and part[0].isalnum():
                out.append(" ")
        out.append(part)
    return "".join(out)


def render_inline(node, source) -> str:
    if isinstance(node, str):
        return html.escape(node)
    if node.tag == "br":
        return "<br>"
    if node.tag == "wbr":
        return "<wbr>"
    if node.tag in ("i", "em"):
        return f"<i>{''.join(render_inline(c, source) for c in node.children)}</i>"
    if node.tag in ("b", "strong"):
        return f"<strong>{''.join(render_inline(c, source) for c in node.children)}</strong>"
    if node.tag == "a":
        return render_link(node, source)
    return glue(render_inline(c, source) for c in node.children)


def render_link(node: Node, source: str) -> str:
    href = abs_url(node.attrs.get("href", ""), source)
    label = "".join(render_inline(c, source) for c in node.children)
    plain = re.sub(r"<[^>]+>", "", label)
    plain = re.sub(r"\s+", " ", plain).strip()
    classes = node.cls()
    buttonish = any(k in classes for k in ("btn", "cta", "word-cta"))
    booking_label = bool(re.fullmatch(
        r"(schedule your free discovery call(?: today)?|book a free discovery call)(?:\s|→|&rarr;)*",
        plain,
        re.I,
    ))
    if is_booking(href) and (buttonish or booking_label):
        label = "Book a free discovery call"
        extra = ' target="_blank" rel="noopener noreferrer"'
        cls = "btn btn--primary"
    else:
        extra = ""
        if node.attrs.get("target"):
            extra += f' target="{attr_esc(node.attrs["target"])}"'
        if node.attrs.get("rel"):
            extra += f' rel="{attr_esc(node.attrs["rel"])}"'
        if href.startswith("tel:"):
            cls = "btn btn--nav" if buttonish else ""
        elif href.startswith("sms:"):
            if buttonish or plain.lower().startswith("text"):
                label = "Text us"
            cls = "btn btn--nav" if buttonish or plain.lower().startswith("text") else ""
        else:
            cls = ""
    class_attr = f' class="{cls}"' if cls else ""
    if not label.strip():
        label = html.escape(plain or href)
    return f'<a href="{attr_esc(href)}"{class_attr}{extra}>{label}</a>'


def responsive_img(src: str, alt: str, cls: str = "", priority: bool = False, sizes: str = "(max-width: 900px) 100vw, 720px") -> str:
    """Add real dimensions and an 800px-wide WebP for large photos."""
    width = height = ""
    srcset = ""
    local = ROOT / src.lstrip("/") if src.startswith("/img/") else None
    if local and local.exists() and local.is_file():
        try:
            with Image.open(local) as im:
                W, H = im.size
                width, height = str(W), str(H)
                if W > 900:
                    dest = ROOT / "img" / "opt" / f"{local.stem}-800.webp"
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.exists() or dest.stat().st_mtime < local.stat().st_mtime:
                        frame = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
                        thumb = frame.copy()
                        thumb.thumbnail((800, 1400), Image.Resampling.LANCZOS)
                        thumb.save(dest, "WEBP", quality=68, method=4)
                    srcset = (
                        f' srcset="/img/opt/{dest.name} 800w, {src} {W}w" sizes="{sizes}"'
                    )
        except Exception:
            pass
    wh = ""
    if width:
        wh = f' width="{width}" height="{height}"'
    load = 'fetchpriority="high" loading="eager"' if priority else 'loading="lazy"'
    class_attr = f' class="{cls}"' if cls else ""
    return (
        f'<img{class_attr} src="{attr_esc(src)}" alt="{attr_esc(alt)}"{wh}{srcset} '
        f'{load} decoding="async">'
    )


def render_img(node: Node, source: str) -> str:
    src = abs_url(node.attrs.get("src", ""), source)
    alt = node.attrs.get("alt", "")
    if src.startswith("/img/"):
        return responsive_img(src, alt)
    extra = ""
    if node.attrs.get("width"):
        extra += f' width="{attr_esc(node.attrs["width"])}"'
    if node.attrs.get("height"):
        extra += f' height="{attr_esc(node.attrs["height"])}"'
    return (
        f'<img src="{attr_esc(src)}" alt="{attr_esc(alt)}"{extra} '
        f'loading="lazy" decoding="async">'
    )


def render_faq(node: Node, source: str) -> str:
    summary = None
    for c in node.children:
        if isinstance(c, Node) and c.tag == "summary":
            summary = c
            break
    question = text_of(summary).strip() if summary else "Question"
    fid = next_faq_id()
    body_parts = []
    for c in node.children:
        if c is summary:
            continue
        body_parts.append(render_node(c, source))
    body = "".join(body_parts).strip() or "<p></p>"
    if not body.startswith("<"):
        body = f"<p>{body}</p>"
    return (
        '<div class="accordion__item">'
        f'<h3><button class="accordion__trigger" type="button" aria-expanded="false" '
        f'aria-controls="{fid}">{html.escape(question)}</button></h3>'
        f'<div class="accordion__panel" id="{fid}">{body}</div>'
        "</div>"
    )


def render_step(node: Node, source: str) -> str:
    title = ""
    h = find_first(node, "h3") or find_first(node, "h4")
    if h:
        title = "".join(render_inline(c, source) for c in h.children)
    paras = []
    for p in find_all(node, "p"):
        paras.append("<p>" + "".join(render_inline(c, source) for c in p.children) + "</p>")
    label = ""
    for c in node.children:
        if isinstance(c, Node) and c.has_class("label"):
            label = text_of(c).strip()
            break
    if not label:
        for c in node.children:
            if isinstance(c, Node) and (c.has_class("num") or c.has_class("marker")):
                bit = text_of(c).strip()
                if bit:
                    label = bit
                    break
    meta_html = ""
    for c in walk(node):
        if isinstance(c, Node) and c.has_class("meta"):
            spans = []
            for s in c.children:
                if isinstance(s, Node):
                    bit = "".join(render_inline(x, source) for x in s.children).strip()
                    if bit:
                        spans.append(f"<span>{bit}</span>")
            if spans:
                meta_html = '<div class="specs">' + "".join(spans) + "</div>"
            break
    index = html.escape(label or "")
    return (
        '<li class="process-steps__item">'
        f'<span class="process-steps__index">{index}</span>'
        f"<div><h3>{title}</h3>{''.join(paras)}{meta_html}</div>"
        "</li>"
    )


def render_quote(node: Node, source: str) -> str:
    quote_node = find_first(node, "blockquote")
    quote = text_of(quote_node).strip() if quote_node else ""
    name = ""
    meta = ""
    for c in find_all(node, "p") + find_all(node, "span"):
        if c.has_class("t-name") or c.has_class("name"):
            name = text_of(c).strip()
        elif c.has_class("t-meta") or c.has_class("tag") or c.has_class("who"):
            meta = re.sub(r"\s+", " ", text_of(c)).strip()
    if not name:
        who = None
        for c in node.children:
            if isinstance(c, Node) and c.has_class("who"):
                who = c
        if who:
            name_el = next((x for x in who.children if isinstance(x, Node) and x.has_class("name")), None)
            tag_el = next((x for x in who.children if isinstance(x, Node) and x.has_class("tag")), None)
            if name_el:
                name = text_of(name_el).strip()
            if tag_el:
                meta = text_of(tag_el).strip()
    cite = " · ".join(x for x in (name, meta) if x)
    href = node.attrs.get("href")
    google = ""
    if href:
        google = f' <a href="{attr_esc(abs_url(href, source))}" target="_blank" rel="noopener noreferrer">View on Google</a>'
    return (
        "<blockquote>"
        f"<p>&ldquo;{html.escape(quote)}&rdquo;</p>"
        f"<cite>{html.escape(cite)}{google}</cite>"
        "</blockquote>"
    )


def render_spread(node: Node, source: str) -> str:
    img = find_first(node, "img")
    h = find_first(node, "h3")
    title = "".join(render_inline(c, source) for c in h.children) if h else ""
    eyebrow = ""
    for c in walk(node):
        if isinstance(c, Node) and c.has_class("eyebrow"):
            eyebrow = re.sub(r"\s+", " ", text_of(c)).strip()
            break
    paras = []
    for p in find_all(node, "p"):
        paras.append("<p>" + "".join(render_inline(c, source) for c in p.children) + "</p>")
    link = None
    for a in find_all(node, "a"):
        link = a
        break
    img_html = "".join(render_img(img_node, source) for img_node in find_all(node, "img"))
    eye_html = f'<p class="eyebrow">{html.escape(eyebrow)}</p>' if eyebrow else ""
    caps = []
    for cap in find_all(node, "figcaption"):
        bit = re.sub(r"\s+", " ", text_of(cap)).strip()
        if bit and bit != eyebrow:
            caps.append(f"<figcaption>{html.escape(bit)}</figcaption>")
    inner = f"{img_html}{eye_html}{''.join(caps)}<h3>{title}</h3>{''.join(paras)}"
    if link:
        href = abs_url(link.attrs.get("href", ""), source)
        more = re.sub(r"\s+", " ", text_of(link)).strip() or "Learn more"
        return (
            f'<a class="service-card" href="{attr_esc(href)}">{inner}'
            f'<span class="service-card__more">{html.escape(more)}</span></a>'
        )
    return f'<article class="info-card">{inner}</article>'


def contact_form() -> str:
    return """<form class="lead-form lead-form--light" id="contact-form" action="#" method="post" novalidate>
  <p class="todo-note">TODO: the live contact form is a GoHighLevel embed, and its exact field list is not in the site source. This preview asks for name, email, phone, and a message, and it does not submit anywhere.</p>
  <div class="lead-form__row"><label for="cf-name">Name *</label><input id="cf-name" name="name" type="text" autocomplete="name" required></div>
  <div class="lead-form__row"><label for="cf-email">Email *</label><input id="cf-email" name="email" type="email" autocomplete="email" required></div>
  <div class="lead-form__row"><label for="cf-phone">Phone</label><input id="cf-phone" name="phone" type="tel" autocomplete="tel"></div>
  <div class="lead-form__row lead-form__row--full"><label for="cf-message">Message *</label><textarea id="cf-message" name="message" rows="5" required></textarea></div>
  <div class="lead-form__row--full"><button class="btn btn--primary" type="submit">Send message</button></div>
  <p class="lead-form__note lead-form__row--full" data-form-note role="status" aria-live="polite"></p>
</form>"""


def newsletter_form() -> str:
    return """<form class="lead-form lead-form--light" id="newsletter-form" action="#" method="post">
  <p class="todo-note">TODO: this preview does not submit the newsletter form. No address is sent.</p>
  <div class="lead-form__row lead-form__row--full"><label for="nl-email">Email *</label><input id="nl-email" name="email" type="email" autocomplete="email" required placeholder="your@email.com"></div>
  <div class="lead-form__row--full"><button class="btn btn--primary" type="submit">Sign up for free</button></div>
  <p class="lead-form__note lead-form__row--full" data-form-note role="status" aria-live="polite"></p>
</form>"""


def render_node(node, source) -> str:
    if isinstance(node, str):
        if not node.strip():
            return ""
        return html.escape(node)
    if node.tag == "comment":
        data = node.attrs.get("data", "").strip()
        if "TODO" in data and "HIDDEN" not in data:
            return f'<p class="todo-note">{html.escape(re.sub(r"\s+", " ", data))}</p>'
        return ""
    if node.tag in ("script", "style", "svg", "noscript"):
        return ""
    if node.tag == "iframe":
        src = node.attrs.get("src", "")
        if "leadconnector" in src or "msgsndr" in src:
            return contact_form()
        return ""
    if node.tag == "form":
        action = node.attrs.get("action", "")
        if "formsubmit" in action or "newsletter" in node.cls():
            return newsletter_form()
        return contact_form()
    if node.tag == "details":
        return render_faq(node, source)
    if is_step(node):
        return render_step(node, source)
    if is_quote(node):
        return render_quote(node, source)
    if is_spread(node):
        return render_spread(node, source)
    if node.tag == "img":
        return render_img(node, source)
    if node.has_class("stamp"):
        bit = re.sub(r"\s+", " ", text_of(node)).strip()
        return f"<figcaption>{html.escape(bit)}</figcaption>" if bit else ""
    if node.tag == "a":
        return render_link(node, source)
    if node.tag == "h1":
        return ""
    if node.tag == "h2":
        inner = "".join(render_inline(c, source) for c in node.children)
        if not re.sub(r"<[^>]+>", "", inner).strip():
            return ""
        return f"<h2>{inner}</h2>"
    if node.tag in ("h3", "h4"):
        inner = "".join(render_inline(c, source) for c in node.children)
        if not re.sub(r"<[^>]+>", "", inner).strip():
            return ""
        return f"<{node.tag}>{inner}</{node.tag}>"
    if node.tag == "p":
        inner = "".join(render_inline(c, source) for c in node.children).strip()
        if not re.sub(r"<[^>]+>", "", inner).strip():
            return ""
        return f"<p>{inner}</p>"
    if node.tag == "blockquote":
        inner = "".join(render_node(c, source) for c in node.children).strip()
        return f"<blockquote>{inner}</blockquote>"
    if node.tag == "li":
        inner = "".join(render_node(c, source) for c in node.children).strip()
        return f"<li>{inner}</li>"
    if node.tag in ("ul", "ol"):
        inner = "".join(render_node(c, source) for c in node.children)
        cls = "check-list" if any(k in node.cls() for k in ("intro-checks", "check", "quick-list")) else ""
        class_attr = f' class="{cls}"' if cls else ""
        return f"<{node.tag}{class_attr}>{inner}</{node.tag}>"
    if node.tag == "figcaption":
        inner = "".join(render_inline(c, source) for c in node.children).strip()
        if not inner:
            return ""
        return f"<figcaption>{inner}</figcaption>"
    if node.tag == "figure":
        inner = "".join(render_node(c, source) for c in node.children)
        return f"<figure>{inner}</figure>"
    # Group consecutive specials inside generic containers.
    return render_children(node.children, source)


def render_children(children, source) -> str:
    out = []
    i = 0
    items = [c for c in children if not (isinstance(c, str) and not c.strip())]
    while i < len(items):
        node = items[i]
        if isinstance(node, Node) and id(node) in SKIP:
            i += 1
            continue
        if is_step(node):
            group = []
            while i < len(items) and is_step(items[i]):
                group.append(render_step(items[i], source))
                i += 1
            out.append('<ol class="process-steps">' + "".join(group) + "</ol>")
            continue
        if is_quote(node):
            group = []
            while i < len(items) and is_quote(items[i]):
                group.append(render_quote(items[i], source))
                i += 1
            out.append('<div class="testimonial-stack">' + "".join(group) + "</div>")
            continue
        if is_spread(node):
            group = []
            while i < len(items) and is_spread(items[i]):
                group.append(render_spread(items[i], source))
                i += 1
            out.append('<div class="service-grid service-grid--three">' + "".join(group) + "</div>")
            continue
        if isinstance(node, Node) and node.tag == "details":
            group = []
            while i < len(items) and isinstance(items[i], Node) and items[i].tag == "details":
                group.append(render_faq(items[i], source))
                i += 1
            out.append('<div class="accordion">' + "".join(group) + "</div>")
            continue
        if isinstance(node, Node) and class_has(node, "specs"):
            bits = []
            for c in node.children:
                if isinstance(c, Node):
                    t = "".join(render_inline(x, source) for x in c.children).strip()
                    if t:
                        bits.append(f"<span>{t}</span>")
                elif c.strip():
                    bits.append(f"<span>{html.escape(c.strip())}</span>")
            out.append('<div class="specs">' + "".join(bits) + "</div>")
            i += 1
            continue
        if isinstance(node, Node) and class_has(node, "compare"):
            out.append(render_node(node, source).replace("<div>", '<div class="compare">', 1) if False else wrap_compare(node, source))
            i += 1
            continue
        if isinstance(node, Node) and node.has_class("num") and node.tag != "h2":
            # Section eyebrows are rendered separately.
            i += 1
            continue
        piece = render_node(node, source) if isinstance(node, Node) else html.escape(node)
        if piece.strip():
            out.append(piece)
        i += 1
    return glue(out)


def wrap_compare(node: Node, source: str) -> str:
    cols = []
    for c in node.children:
        if isinstance(c, Node) and ("col" in c.cls().split() or c.has_class("col")):
            label = ""
            verdict = ""
            for ch in c.children:
                if isinstance(ch, Node) and ch.has_class("label"):
                    label = text_of(ch).strip()
                elif isinstance(ch, Node):
                    verdict += "".join(render_inline(x, source) for x in ch.children)
            cash = " cash" if c.has_class("cash") else ""
            cols.append(
                f'<div class="col{cash}"><span class="label">{html.escape(label)}</span><p>{verdict}</p></div>'
            )
    return '<div class="compare">' + "".join(cols) + "</div>"


def eyebrow_of(section: Node) -> str:
    for c in walk(section):
        if not isinstance(c, Node):
            continue
        if c.has_class("num") or "eyebrow" in c.cls():
            t = re.sub(r"\s+", " ", text_of(c)).strip()
            if t and len(t) < 80:
                return t
    return ""


def walk(node):
    if isinstance(node, Node):
        yield node
        for c in node.children:
            yield from walk(c)


def first_paragraph(section: Node):
    for c in walk(section):
        if isinstance(c, Node) and c.tag == "p":
            return c
    return None


def top_blocks(main: Node):
    blocks = []

    def rec(node, inside):
        for c in node.children:
            if not isinstance(c, Node):
                continue
            if c.tag == "comment" and not inside:
                blocks.append(c)
            elif c.tag in ("section", "header", "aside") and not inside:
                blocks.append(c)
            elif c.tag == "article" and not inside and find_first(c, "h1"):
                # Blog: header inside article, plus following sections.
                rec(c, False)
            else:
                rec(c, inside)

    rec(main, False)
    if not blocks:
        blocks = [main]
    return blocks


def hero_from(block: Node, source: str, fallback_image=None) -> str:
    h1 = find_first(block, "h1")
    title = "".join(render_inline(c, source) for c in h1.children) if h1 else "Island PT"
    eyebrow = eyebrow_of(block)
    lead_node = None
    for c in walk(block):
        if isinstance(c, Node) and c.tag == "p" and (c.has_class("lead") or c.has_class("subhead")):
            lead_node = c
            break
    if lead_node is None:
        lead_node = first_paragraph(block)
    lead = ""
    if lead_node:
        lead = "".join(render_inline(c, source) for c in lead_node.children)
        lead = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", lead)).strip()
        # The lead sometimes swallows a CTA label. Cut at a booking phrase.
        lead = re.split(r"\s*(Book a free discovery call|Schedule your free discovery call).*$", lead)[0].strip()
    img = find_first(block, "img")
    if img:
        src = abs_url(img.attrs.get("src", ""), source)
        alt = img.attrs.get("alt", "")
        hero_img = responsive_img(src, alt, cls="hero__image", priority=True, sizes="100vw")
        plain = ""
    elif fallback_image:
        src, alt = fallback_image
        hero_img = responsive_img(src, alt, cls="hero__image", priority=True, sizes="100vw")
        plain = ""
    else:
        hero_img = ""
        plain = " hero--plain"
    actions = hero_actions(block, source)
    eye = f'<p class="eyebrow">{html.escape(eyebrow)}</p>' if eyebrow else ""
    sub = f'<p class="subhead">{html.escape(lead)}</p>' if lead else ""
    stamps = []
    for c in walk(block):
        if isinstance(c, Node) and c.has_class("stamp"):
            bit = re.sub(r"\s+", " ", text_of(c)).strip()
            if bit and bit not in stamps:
                stamps.append(bit)
    stamp_html = "".join(f'<p class="hero__guide-link">{html.escape(bit)}</p>' for bit in stamps)
    return f"""<header class="hero hero--page{plain}">
  {hero_img}
  <div class="hero__scrim" aria-hidden="true"></div>
  <div class="hero__content reveal">
    {eye}
    <h1>{title}</h1>
    {sub}
    {stamp_html}
    <nav class="hero-cta" aria-label="Page actions">{actions}</nav>
  </div>
</header>"""


def hero_actions(block: Node, source: str) -> str:
    """Every hero offers Call, Text us, and the discovery call, in that order."""
    return (
        f'<a class="btn btn--secondary" href="{PHONE_TEL}">Call {PHONE_DISPLAY}</a>'
        f'<a class="btn btn--secondary" href="{PHONE_SMS}">Text us</a>'
        f'<a class="btn btn--primary" href="{BOOK}" target="_blank" rel="noopener noreferrer">Book a free discovery call</a>'
    )


def used_in_hero(block: Node):
    """Nodes whose text is already represented in the hero, so the body can skip them."""
    skip = set()
    h1 = find_first(block, "h1")
    if h1:
        skip.add(id(h1))
    img = find_first(block, "img")
    if img:
        skip.add(id(img))
    for c in walk(block):
        if not isinstance(c, Node):
            continue
        if c.has_class("num") or c.has_class("signature") or c.has_class("stamp") or "eyebrow" in c.cls():
            skip.add(id(c))
    for a in find_all(block, "a"):
        href = a.attrs.get("href", "")
        if href.startswith("tel:") or href.startswith("sms:") or is_booking(href) or href.startswith("#"):
            skip.add(id(a))
    for c in walk(block):
        if isinstance(c, Node) and c.tag == "p" and (c.has_class("lead") or c.has_class("subhead")):
            skip.add(id(c))
            break
    else:
        p = first_paragraph(block)
        if p:
            skip.add(id(p))
    return skip


def section_html(block: Node, source: str, tint: bool, skip_ids) -> str:
    global SKIP
    eye = ""
    for c in walk(block):
        if isinstance(c, Node) and c.has_class("num"):
            t = re.sub(r"\s+", " ", text_of(c)).strip()
            if t:
                eye = t
                break
    if not eye:
        for c in walk(block):
            if isinstance(c, Node) and c.has_class("eyebrow") and id(c) not in skip_ids:
                t = re.sub(r"\s+", " ", text_of(c)).strip()
                if t and len(t) < 80:
                    eye = t
                    break
    SKIP = set(skip_ids)
    body = render_children(block.children, source)
    SKIP = set()
    if not re.sub(r"<[^>]+>", "", body).strip():
        return ""
    sid = block.attrs.get("id")
    id_attr = f' id="{attr_esc(sid)}"' if sid else ""
    tint_cls = " section--tinted" if tint else ""
    eye_html = f'<p class="eyebrow">{html.escape(eye)}</p>' if eye else ""
    header = f'<div class="section__header reveal">{eye_html}</div>' if eye_html else ""
    return f"""<section class="section{tint_cls}"{id_attr}>
  {header}
  <div class="prose reveal">{body}</div>
</section>"""


def meta_content(doc: str, name: str) -> str:
    pattern = rf'<meta[^>]+(?:name|property)="{re.escape(name)}"[^>]+content="([^"]*)"'
    m = re.search(pattern, doc, re.I)
    if not m:
        pattern = rf'<meta[^>]+content="([^"]*)"[^>]+(?:name|property)="{re.escape(name)}"'
        m = re.search(pattern, doc, re.I)
    return html.unescape(m.group(1)) if m else ""


def jsonld_blocks(doc: str) -> str:
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', doc, re.S
    )
    return "\n".join(f'<script type="application/ld+json">{b}</script>' for b in blocks)


def current_path(source: str) -> str:
    if source == "index.html":
        return "/"
    if source.endswith("/index.html"):
        return "/" + source[: -len("/index.html")]
    return "/" + source


def nav_current(href: str, here: str) -> str:
    if href == "/blog" and (here == "/blog" or here.startswith("/blog/")):
        return ' aria-current="page"'
    if href == here:
        return ' aria-current="page"'
    return ""


def dropdown(label, links, menu_id, here, mobile=False):
    active = any(nav_current(href, here) for _, href in links)
    current = ' aria-current="true"' if active else ""
    items = []
    for text, href in links:
        items.append(
            f'<a class="nav-subitem" role="menuitem" href="{href}"{nav_current(href, here)}>{text}</a>'
        )
    return f"""<div class="nav-dropdown">
      <button type="button" class="nav-item nav-dropdown__toggle" aria-expanded="false" aria-haspopup="true" aria-controls="{menu_id}"{current}>{label}</button>
      <div class="nav-dropdown__panel" id="{menu_id}" role="menu" aria-label="{attr_esc(label)}">
        {''.join(items)}
      </div>
    </div>"""


def nav_html(here: str) -> str:
    desktop = []
    mobile = []
    for i, item in enumerate(NAV):
        label = item[0]
        if isinstance(item[1], list):
            desktop.append(dropdown(label, item[1], f"menu-{i}", here))
            mobile.append(dropdown(label, item[1], f"menu-{i}-mobile", here, True))
        else:
            href = item[1]
            desktop.append(f'<a class="nav-item" href="{href}"{nav_current(href, here)}>{label}</a>')
            mobile.append(f'<a class="nav-item" href="{href}"{nav_current(href, here)}>{label}</a>')
    return f"""<header class="site-nav" id="site-nav">
  <div class="site-nav__inner">
    <a href="/" class="site-nav__logo" aria-label="Island PT, home">
      <img src="/img/island-pt-logo.webp" alt="Island PT" width="760" height="291">
    </a>
    <div class="site-nav__mobile-calls">
      <a class="btn btn--nav-primary" href="{PHONE_TEL}" aria-label="Call {PHONE_DISPLAY}">Call</a>
      <a class="btn btn--nav" href="{PHONE_SMS}">Text us</a>
    </div>
    <nav class="site-nav__links" aria-label="Primary">
      {''.join(desktop)}
    </nav>
    <div class="site-nav__actions">
      <a class="btn btn--nav" href="{PHONE_TEL}">Call</a>
      <a class="btn btn--nav" href="{PHONE_SMS}">Text us</a>
      <a class="btn btn--nav-primary" href="{BOOK}" target="_blank" rel="noopener noreferrer">Book a free discovery call</a>
    </div>
    <button class="site-nav__toggle" id="nav-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="site-nav__mobile">
      <span class="site-nav__toggle-icon" aria-hidden="true"><span></span><span></span><span></span></span>
      <span class="site-nav__toggle-label">Menu</span>
    </button>
  </div>
  <nav class="site-nav__mobile" id="site-nav__mobile" aria-label="Mobile">
    {''.join(mobile)}
    <a class="btn btn--nav" href="{PHONE_TEL}">Call {PHONE_DISPLAY}</a>
    <a class="btn btn--nav" href="{PHONE_SMS}">Text us</a>
    <a class="btn btn--primary" href="{BOOK}" target="_blank" rel="noopener noreferrer">Book a free discovery call</a>
  </nav>
</header>
<div class="sticky-cta" id="sticky-cta">
  <p>Book a free discovery call</p>
  <div class="sticky-cta__actions">
    <a href="{PHONE_TEL}" class="btn btn--sticky-call">Call</a>
    <a href="{PHONE_SMS}" class="btn btn--sticky-call">Text us</a>
    <a href="{BOOK}" class="btn btn--sticky" target="_blank" rel="noopener noreferrer">Book a free discovery call</a>
  </div>
</div>"""


def footer_html() -> str:
    return f"""<footer class="site-footer">
  <div class="site-footer__inner">
    <div class="site-footer__cols">
      <div>
        <img class="site-footer__logo" src="/img/island-pt-logo.webp" alt="Island PT" width="760" height="291" loading="lazy">
        <p>Island PT is Maui’s premier concierge physical therapy practice, delivering personalized care and clinical expertise through comprehensive evaluations and hands-on treatment in your own home.</p>
        <p><a href="{CRED}" target="_blank" rel="noopener noreferrer"><img src="{BADGE}" alt="ABPTS Board-Certified Orthopaedic Clinical Specialist badge, issued by the American Physical Therapy Association" width="56" height="56" loading="lazy"></a></p>
        <p><strong>Teddy Zabel, DPT, OCS</strong><br>Board-Certified Orthopaedic Clinical Specialist · American Physical Therapy Association · <a href="{CRED}" target="_blank" rel="noopener noreferrer">Verify credential</a></p>
      </div>
      <div>
        <h2>Contact</h2>
        <p><a href="{PHONE_TEL}">{PHONE_DISPLAY}</a></p>
        <p><a href="{PHONE_SMS}">Text us</a></p>
        <p><a href="mailto:{EMAIL}">{EMAIL}</a></p>
        <p>Monday – Friday<br>8 AM – 6 PM</p>
        <p>Kīhei, Maui · In-home visits</p>
      </div>
      <div>
        <h2>Explore</h2>
        <nav aria-label="Footer">
          <a href="{BOOK}" target="_blank" rel="noopener noreferrer">Book a free discovery call</a>
          <a href="/services.html">Our Services</a>
          <a href="/mobile-physical-therapy.html">Mobile Physical Therapy</a>
          <a href="/about.html">Our Story</a>
          <a href="/why-cash-pay.html">Why Cash-Pay</a>
          <a href="/blog">Blog</a>
          <a href="/testimonials.html">Reviews</a>
          <a href="/contact.html">Contact</a>
          <a href="/service-area.html">Service Area</a>
        </nav>
      </div>
      <div>
        <h2>Where we visit</h2>
        <nav aria-label="Cities">
          <a href="/physical-therapy-kihei.html">Kīhei</a>
          <a href="/physical-therapy-wailea.html">Wailea</a>
          <a href="/physical-therapy-makena.html">Mākena</a>
          <a href="/physical-therapy-kahului.html">Kahului</a>
          <a href="/physical-therapy-kula.html">Kula</a>
          <a href="/physical-therapy-makawao.html">Makawao</a>
        </nav>
      </div>
    </div>
  </div>
  <p class="site-footer__legal">&copy; <span id="year"></span> Island PT · All Rights Reserved · <a href="/privacy-policy.html">Privacy Policy</a> · <a href="/terms.html">Terms &amp; Conditions</a></p>
</footer>"""


def page_shell(source, title, description, canonical, image, ld, body) -> str:
    desc = attr_esc(description)
    title_esc = html.escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_esc}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex, nofollow">
<link rel="canonical" href="{attr_esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Island PT">
<meta property="og:title" content="{title_esc}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{attr_esc(canonical)}">
<meta property="og:image" content="{attr_esc(image)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title_esc}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{attr_esc(image)}">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&amp;family=Manrope:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="/styles.css">
<link rel="stylesheet" href="/ipt.css">
<script>document.documentElement.classList.add("js-reveal");</script>
{ld}
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
{nav_html(current_path(source))}
<main id="main">
{body}
</main>
{footer_html()}
<script src="/script.js"></script>
</body>
</html>
"""


def build_body(doc: str, source: str) -> str:
    global _faq_n
    _faq_n = 0
    tree = parse(doc)
    mains = find_all(tree, "main")
    if not mains:
        return "<section class='section'><p>TODO: this page had no main content in the source.</p></section>"
    main = mains[0]
    blocks = top_blocks(main)
    parts = []
    hero_done = False
    tint = False
    for block in blocks:
        if block.tag == "comment":
            parts.append(render_node(block, source))
            continue
        if not hero_done and find_first(block, "h1"):
            parts.append(hero_from(block, source, HERO_IMAGE.get(source)))
            hero_done = True
            skip = used_in_hero(block)
            rest = section_html(block, source, tint, skip)
            plain = re.sub(r"<[^>]+>", " ", rest)
            plain = re.sub(r"\s+", " ", plain).strip()
            if plain:
                parts.append(rest)
                tint = not tint
            continue
        html_block = section_html(block, source, tint, set())
        if html_block.strip():
            parts.append(html_block)
            tint = not tint
    if not hero_done:
        h1 = find_first(main, "h1")
        if h1:
            parts.insert(0, hero_from(main, source, HERO_IMAGE.get(source)))
    return "\n".join(parts)


def visible_words(fragment: str) -> list[str]:
    fragment = re.sub(r"<!--.*?-->", " ", fragment, flags=re.S)
    fragment = re.sub(r"<script[\s\S]*?</script>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<style[\s\S]*?</style>", " ", fragment, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = html.unescape(text)
    text = text.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return re.findall(r"[a-z0-9']+", text.lower())


def audit(source_doc: str, output_doc: str, source: str) -> list[str]:
    src_main = re.search(r"<main[\s\S]*?</main>", source_doc, re.I)
    out_main = re.search(r"<main[\s\S]*?</main>", output_doc, re.I)
    if not src_main or not out_main:
        return [f"{source}: missing main"]
    src_words = visible_words(src_main.group(0))
    out_words = visible_words(out_main.group(0))
    out_set = set(out_words)
    # Flag uncommon source words missing from the output (names, places, numbers).
    missing = []
    seen = set()
    for w in src_words:
        if w in seen or w in out_set:
            continue
        if len(w) < 4:
            continue
        if w in {"with", "that", "this", "from", "your", "have", "been", "will", "what", "when", "they", "them", "into", "about", "more", "than"}:
            continue
        seen.add(w)
        missing.append(w)
    return missing[:25]


def build_page(source: str) -> tuple[str, list[str]]:
    doc = git_show(source)
    title = re.search(r"<title>(.*?)</title>", doc, re.S)
    title = re.sub(r"\s+", " ", html.unescape(title.group(1))).strip() if title else "Island PT"
    description = meta_content(doc, "description")
    canonical = ""
    m = re.search(r'rel="canonical" href="([^"]+)"', doc)
    if m:
        canonical = m.group(1)
    else:
        canonical = "https://www.islandptmaui.com" + current_path(source)
    image = meta_content(doc, "og:image") or "https://www.islandptmaui.com/img/IslandPT_Logo.png"
    body = build_body(doc, source)
    page = page_shell(source, title, description, canonical, image, jsonld_blocks(doc), body)
    return page, audit(doc, page, source)


def not_found() -> str:
    body = f"""<header class="hero hero--page hero--plain">
  <div class="hero__content">
    <p class="eyebrow">Island PT</p>
    <h1>Page not found.</h1>
    <p class="subhead">That page is not on this preview. The live site is unchanged.</p>
    <nav class="hero-cta" aria-label="Page actions">
      <a class="btn btn--secondary" href="{PHONE_TEL}">Call {PHONE_DISPLAY}</a>
      <a class="btn btn--secondary" href="{PHONE_SMS}">Text us</a>
      <a class="btn btn--primary" href="/">Back home</a>
    </nav>
  </div>
</header>"""
    return page_shell(
        "404.html",
        "Page not found — Island PT",
        "That page is not on this Island PT preview.",
        "https://www.islandptmaui.com/404.html",
        "https://www.islandptmaui.com/img/IslandPT_Logo.png",
        "",
        body,
    )


def preserve_design_system():
    """The live specimen page is a catalog of the previous system. Keep it intact and noindex it."""
    doc = git_show("design-system.html")
    doc = re.sub(
        r'<meta name="robots" content="[^"]*"\s*/?>',
        '<meta name="robots" content="noindex, nofollow">',
        doc,
        count=1,
    )
    (ROOT / "design-system.html").write_text(doc)
    print("kept design-system.html (noindex, nofollow)")


def main():
    reports = []
    for source in PAGES:
        page, missing = build_page(source)
        dest = ROOT / source
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page)
        reports.append((source, missing))
        print(f"wrote {source} ({len(page)} bytes) missing_words={len(missing)}")
        if missing:
            print("  ", ", ".join(missing[:18]))
    (ROOT / "404.html").write_text(not_found())
    print("wrote 404.html")
    preserve_design_system()
    return reports


if __name__ == "__main__":
    main()
