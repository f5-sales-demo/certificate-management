"""Exercise every English route, TOC, and task navigation in both appearances."""

import argparse
import json
import os
import shutil
from functools import partial
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import Error as PlaywrightError, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def record_error(errors: list[str], error: PlaywrightError) -> None:
    """Bind each browser context to its own error collection."""
    errors.append(str(error))


def verify_page(page: Page, url: str, route: str, appearance: str) -> None:
    """Check the rendered title, appearance, page width, and active sidebar item."""
    response = page.goto(url, wait_until="networkidle")
    assert response is not None
    assert response.status == 200, url
    assert page.locator("main h1").count() == 1, route
    assert page.locator("html").get_attribute("data-theme") == appearance, route
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
        route
    )
    active = page.locator('.sidebar-content a[aria-current="page"]')
    assert active.count() == 1, route
    assert active.evaluate("e => e.href") == url, (
        route,
        active.evaluate("e => e.href"),
    )


def verify_toc(page: Page, width: int, height: int, route: str) -> int:
    """Use keyboard section navigation and verify headings below all sticky navigation."""
    page.add_style_tag(content="html { scroll-behavior: auto !important; }")
    toc = page.locator("mobile-starlight-toc" if width < 800 else "starlight-toc")
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
        sticky_bottom = page.locator(
            "header, nav.breadcrumbs, mobile-starlight-toc"
        ).evaluate_all(
            "es => Math.max(0, ...es.filter(e => "
            '["sticky", "fixed"].includes(getComputedStyle(e).position) && '
            "e.getBoundingClientRect().height > 0).map(e => e.getBoundingClientRect().bottom))"
        )
        assert box is not None
        assert box["y"] >= sticky_bottom - 1, (
            route,
            href,
            width,
            box,
            sticky_bottom,
        )
        assert box["y"] < height, (route, href, width, box)
        assert link.get_attribute("aria-current") == "true", (
            route,
            href,
            width,
            "current TOC section",
        )
        if width < 800:
            assert (
                toc.locator(".display-current").inner_text().strip()
                == (link.text_content() or "").strip()
            ), (route, href, "mobile current section")
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(350)
    active = toc.locator('a[href="' + links[-1] + '"]')
    assert active.get_attribute("aria-current") == "true", (
        route,
        width,
        "fragment reload TOC state",
    )
    if width < 800:
        assert (
            toc.locator(".display-current").inner_text().strip()
            == (active.text_content() or "").strip()
        ), (route, width, "fragment reload mobile label")
        toc.locator("summary").focus()
        if not toc.locator("details").evaluate("e => e.open"):
            page.keyboard.press("Enter")
    top = toc.locator('a[href="#_top"]')
    top.focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(150)
    assert toc.locator('a[href="#_top"]').get_attribute("aria-current") == "true", (
        route,
        width,
        "top section state",
    )
    return len(links)


def verify_sidebar(page: Page, width: int, route: str) -> None:
    """Reveal and focus the current page within the desktop or mobile sidebar."""
    if width < 800:
        menu = page.get_by_role("button", name="Menu", exact=True)
        menu.focus()
        page.keyboard.press("Enter")
    active = page.locator(".sidebar-content a[aria-current=page]")
    assert active.is_visible(), (route, width, "active sidebar link hidden")
    bounds = active.bounding_box()
    panel = page.locator("#starlight__sidebar").bounding_box()
    assert bounds is not None
    assert panel is not None
    assert bounds["y"] >= panel["y"] - 1, (route, width, bounds, panel)
    assert bounds["y"] + bounds["height"] <= panel["y"] + panel["height"] + 1, (
        route,
        width,
        bounds,
        panel,
    )
    active.focus()
    assert active.evaluate("e => e === document.activeElement")
    if width < 800:
        page.get_by_role("button", name="Menu", exact=True).click()


def capture_route(
    page: Page,
    base: str,
    output: Path,
    route: str,
    viewport: tuple[int, int],
    appearance: str,
    errors: list[str],
) -> dict[str, object]:
    """Keep one route's navigation checks and screenshot in the same observation."""
    width, height = viewport
    url = base.rstrip("/") + "/en/" + (route + "/" if route else "")
    verify_page(page, url, route, appearance)
    verify_sidebar(page, width, route)
    link_count = verify_toc(page, width, height, route)
    for link in page.locator(".pagination-links a").all():
        destination = urljoin(url, link.get_attribute("href") or "")
        assert page.request.get(destination).status == 200, (route, destination)
    screenshot = f"{width}-{appearance}-{route.replace('/', '-') or 'overview'}.png"
    page.screenshot(path=str(output / screenshot))
    assert not errors, (route, errors)
    return {
        "route": "/en/" + (route + "/" if route else ""),
        "width": width,
        "appearance": appearance,
        "toc_links": link_count,
        "keyboard_section_navigation": "passed",
        "heading_visibility": "passed",
        "active_sidebar": "passed",
        "pagination": "passed",
        "overflow": "absent",
        "screenshot": screenshot,
    }


def main() -> None:
    """Visit each source route in both viewport sizes and both appearances."""
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
    observations: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        executable = (
            os.environ.get("CERT_BROWSER_EXECUTABLE")
            or shutil.which("google-chrome")
            or shutil.which("chromium")
        )
        browser = playwright.chromium.launch(executable_path=executable, headless=True)
        for width, height in ((1440, 1000), (390, 844)):
            for appearance in ("light", "dark"):
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    color_scheme=appearance,
                    reduced_motion="reduce",
                )
                page = context.new_page()
                errors: list[str] = []
                page.on("pageerror", partial(record_error, errors))
                observations.extend(
                    capture_route(
                        page,
                        args.base,
                        args.output,
                        route,
                        (width, height),
                        appearance,
                        errors,
                    )
                    for route in routes
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
