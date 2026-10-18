"""Exercise every English route, TOC, and task navigation in both appearances."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Keep each screenshot and its route-specific observations together."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    routes = [
        page.relative_to(ROOT / "docs/en")
        .as_posix()
        .removesuffix(".md")
        .removesuffix("index")
        .rstrip("/")
        for page in sorted((ROOT / "docs/en").rglob("*.md"))
    ]
    observations = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get(
                "CERT_BROWSER_EXECUTABLE", "/usr/bin/google-chrome"
            ),
            headless=True,
        )
        for width, height in ((1440, 1000), (390, 844)):
            for appearance in ("light", "dark"):
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    color_scheme=appearance,
                    reduced_motion="reduce",
                )
                page = context.new_page()
                errors = []
                page.on(
                    "pageerror", lambda error, errors=errors: errors.append(str(error))
                )
                for route in routes:
                    url = (
                        args.base.rstrip("/") + "/en/" + (route + "/" if route else "")
                    )
                    response = page.goto(url, wait_until="networkidle")
                    assert response.status == 200, url
                    assert page.locator("main h1").count() == 1, route
                    assert (
                        page.locator("html").get_attribute("data-theme") == appearance
                    ), route
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth + 1"
                    ), route
                    active = page.locator('.sidebar-content a[aria-current="page"]')
                    assert active.count() == 1, route
                    assert active.evaluate("e => e.href") == url, (
                        route,
                        active.evaluate("e => e.href"),
                    )
                    page.add_style_tag(
                        content="html { scroll-behavior: auto !important; }"
                    )
                    toc = page.locator(
                        "mobile-starlight-toc" if width < 800 else "starlight-toc"
                    )
                    headings = page.locator(
                        "main .sl-markdown-content h2, main .sl-markdown-content h3"
                    ).count()
                    assert toc.locator("nav").is_visible(), (route, width)
                    links = toc.locator('a[href^="#"]').evaluate_all(
                        "es => es.map(e => e.getAttribute('href'))"
                    )
                    assert len(links) >= headings + 1, (route, headings, links)
                    for href in links:
                        if width < 800:
                            summary = toc.locator("summary")
                            summary.focus()
                            if not toc.locator("details").evaluate("e => e.open"):
                                page.keyboard.press("Enter")
                        link = toc.locator('a[href="' + href + '"]')
                        link.focus()
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(100)
                        target = page.locator(href)
                        assert target.count() == 1, (route, href)
                        box = target.bounding_box()
                        header = page.locator("header").first.bounding_box()
                        # A short page can clamp at its final scroll position; headings must remain visible.
                        assert box["y"] >= header["y"] + header["height"] - 1, (
                            route,
                            href,
                            width,
                            box,
                            header,
                        )
                        assert box["y"] < height, (route, href, width, box)
                    pagination = page.locator(".pagination-links a")
                    for link in pagination.all():
                        destination = urljoin(url, link.get_attribute("href"))
                        assert page.request.get(destination).status == 200, (
                            route,
                            destination,
                        )
                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(150)
                    assert toc.locator('a[href="#_top"]').get_attribute("aria-current") == "true", (route, width, "top section state")
                    screenshot = f"{width}-{appearance}-{route.replace('/', '-') or 'overview'}.png"
                    page.screenshot(path=str(args.output / screenshot))
                    assert not errors, (route, errors)
                    observations.append(
                        {
                            "route": "/en/" + (route + "/" if route else ""),
                            "width": width,
                            "appearance": appearance,
                            "toc_links": len(links),
                            "keyboard_section_navigation": "passed",
                            "heading_visibility": "passed",
                            "active_sidebar": "passed",
                            "pagination": "passed",
                            "overflow": "absent",
                            "screenshot": screenshot,
                        }
                    )
                context.close()
        browser.close()
    (args.output / "receipt.json").write_text(
        json.dumps({"observations": observations}, indent=2) + "\n"
    )
    print(  # noqa: T201 -- CLI verification summary.
        f"Usability browser checks passed: {len(observations)} route/viewport/appearance combinations."
    )


if __name__ == "__main__":
    main()
