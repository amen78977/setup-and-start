#!/usr/bin/env python3
"""Optional real-browser smoke/visual evidence using an existing Playwright install.

Only local URLs by default. Does not install browsers/packages or deploy anything.
Captures screenshots and machine-readable signals; human/vision-based assessment
is still required before asserting visual quality.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

VIEWPORTS = {"mobile": (390, 844), "desktop": (1440, 900)}
LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def url_allowed(url: str, remote: bool = False) -> bool:
    parsed = urlsplit(url)
    return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
            and not parsed.username and not parsed.password
            and (remote or parsed.hostname in LOOPBACK))


def assess(metrics: dict) -> dict:
    issues = []
    if metrics.get("overflow_px", 0) > 2:
        issues.append("Horizontal overflow on viewport")
    if metrics.get("broken_images", 0):
        issues.append("Broken images detected")
    if metrics.get("unnamed_buttons", 0):
        issues.append("Buttons with no accessible name")
    if metrics.get("unlabelled_inputs", 0):
        issues.append("Inputs with no associated accessible label")
    if metrics.get("page_errors", 0):
        issues.append("Page JavaScript errors")
    return {"pass": not issues, "issues": issues}


def capture(url: str, output: Path, *, remote: bool = False, timeout_ms: int = 15000) -> dict:
    if not url_allowed(url, remote):
        raise ValueError("Only localhost/loopback URLs are allowed unless --allow-remote is explicitly provided")
    if timeout_ms < 1000 or timeout_ms > 60000:
        raise ValueError("Timeout must be 1000..60000 milliseconds")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Python Playwright is not installed. Install it and browser binaries explicitly.") from exc
    output.mkdir(parents=True, exist_ok=True)
    report = {"url": url, "viewports": {}, "note": "Screenshots require visual review; this is not a full WCAG audit."}
    with sync_playwright() as browser_api:
        browser = browser_api.chromium.launch(headless=True)
        try:
            for key, (width, height) in VIEWPORTS.items():
                page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
                errors = []
                page.on("pageerror", lambda err: errors.append(str(err)[:300]))
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    page.wait_for_timeout(800)
                    measurements = page.evaluate("""() => {
                      const buttons=[...document.querySelectorAll('button,[role=button]')];
                      const inputs=[...document.querySelectorAll('input:not([type=hidden]),select,textarea')];
                      const name=e=>e.getAttribute('aria-label') || e.getAttribute('title')
                        || e.innerText?.trim() || e.textContent?.trim();
                      const labelled=e=>name(e) || (e.id && document.querySelector('label[for="'+CSS.escape(e.id)+'"]'))
                        || e.closest('label') || e.getAttribute('aria-labelledby');
                      return {
                        title:document.title,
                        language:document.documentElement.lang || '',
                        direction:getComputedStyle(document.documentElement).direction,
                        overflow_px:Math.max(0,document.documentElement.scrollWidth-innerWidth),
                        broken_images:[...document.images].filter(i=>!i.complete || i.naturalWidth===0).length,
                        unnamed_buttons:buttons.filter(b=>!name(b)).length,
                        unlabelled_inputs:inputs.filter(i=>!labelled(i)).length
                      };
                    }""")
                    measurements["page_errors"] = len(errors)
                    measurements["page_errors_sample"] = errors[:3]
                    filename = key + ".png"
                    page.screenshot(path=str(output / filename), full_page=True)
                    measurements["screenshot"] = filename
                    measurements["assessment"] = assess(measurements)
                    report["viewports"][key] = measurements
                except Exception as exc:
                    report["viewports"][key] = {"assessment": {"pass": False,
                        "issues": ["Browser capture failed: " + type(exc).__name__]},
                        "error": str(exc)[:300]}
                finally:
                    page.close()
        finally:
            browser.close()
    report["pass"] = all(v["assessment"]["pass"] for v in report["viewports"].values())
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Opt-in browser screenshot and smoke audit")
    parser.add_argument("url", help="http://127.0.0.1:3000 or similar")
    parser.add_argument("--output", default=".setup-start/visual-evidence")
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    args = parser.parse_args()
    try:
        result = capture(args.url, Path(args.output), remote=args.allow_remote, timeout_ms=args.timeout_ms)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
