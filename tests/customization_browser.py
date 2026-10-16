"""Exercise published or locally built guides through real form inputs and clipboard."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("CERT_CUSTOMIZATION_URL", "http://127.0.0.1:18865")
ROOT = BASE + "/certificate-management/en/"
PAGES = [
    "",
    "terraform/",
    "terraform/input-lifecycle/",
    "terraform/certificate-surfaces/",
    "wingman/",
    "wingman/validation/",
    "xcsh/",
    "xcsh/input-workflows/",
    "xcsh/command-reference/",
]
ARTIFACTS = Path(
    os.environ.get(
        "CERT_CUSTOMIZATION_ARTIFACTS",
        tempfile.mkdtemp(prefix="certificate-customization-browser-"),
    )
)
ARTIFACTS.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser_path = (
        os.environ.get("CERT_BROWSER_EXECUTABLE")
        or shutil.which("google-chrome")
        or shutil.which("chromium-browser")
        or shutil.which("chromium")
    )
    browser = (
        p.chromium.launch(executable_path=browser_path, headless=True)
        if browser_path
        else p.chromium.launch(headless=True)
    )
    checks = []
    for width, height in [(1440, 1000), (390, 844)]:
        context = browser.new_context(
            viewport={"width": width, "height": height},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))

        def visit(route, page=page):
            page.goto(ROOT + route)
            page.locator("#placeholder-form").wait_for(state="attached")
            page.locator(".ph-form-wrapper summary").click()

        visit("terraform/")
        assert (
            page.locator("#ph-XCSH_TLS_INPUT_PASSWORD").get_attribute("type")
            == "password"
        )
        assert page.locator("#ph-XCSH_KEY_FILE").get_attribute("type") == "text"
        assert page.locator("#ph-XCSH_API_TOKEN").input_value() == ""
        assert page.locator("#ph-XCSH_TLS_INPUT_PASSWORD").input_value() == ""
        sentinel = (
            'Reader O\'Brien "quote" \\ path $HOME $(id) `id` ${literal} %{literal}'
        )
        values = {
            "XCSH_NAMESPACE": sentinel,
            "XCSH_LB_NAME": sentinel,
            "XCSH_DOMAINNAME": "reader.example.com",
            "XCSH_CERT_FILE": "/private/" + sentinel + ".pem",
            "XCSH_KEY_FILE": "/private/" + sentinel + "-key.pem",
            "XCSH_CERT_ID": sentinel,
            "XCSH_API_TOKEN": "TOKEN_SENTINEL",
            "XCSH_TLS_INPUT_PASSWORD": "PASSPHRASE_SENTINEL",
            "XCSH_WINGMAN_NAME": "reader-wingman",
            "XCSH_WINGMAN_IMAGE": "ghcr.io/f5-sales-demo/certificate-management-wingman@sha256:"
            + "a" * 64,
            "XCSH_KUBECONFIG_FILE": "/private/reader kubeconfig",
            "XCSH_KUBECONFIG_CONTEXT": "reader-context",
            "XCSH_WINGMAN_SITE_SELECTOR": "ves.io/siteName=reader-site",
        }
        for name, value in values.items():
            page.locator("#ph-" + name).fill(value)
        page.locator("#ph-XCSH_WORKDIR").focus()
        canonical_urls = [
            BASE + "/certificate-management/_data/terraform/named-certificate/main.tf",
            BASE + "/certificate-management/assets/certificate-management.pem",
            BASE + "/certificate-management/_data/wingman/contract.json",
            BASE + "/certificate-management/_data/wingman/runtime/main.tf",
            BASE + "/certificate-management/_data/wingman/qualification/main.tf",
        ]
        downloads = {
            url: hashlib.sha256(context.request.get(url).body()).hexdigest()
            for url in canonical_urls
        }
        for route in PAGES:
            visit(route)
            for name, value in values.items():
                assert page.locator("#ph-" + name).input_value() == value, (route, name)
            assert (
                page.locator("#ph-XCSH_TLS_INPUT_PASSWORD").input_value()
                == "PASSPHRASE_SENTINEL"
            )
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            for block in page.locator("[data-xcsh-context] .expressive-code").all():
                block.locator("button[data-code]").click()
                copied = page.evaluate("navigator.clipboard.readText()")
                displayed = block.locator("pre code").text_content()
                assert copied == displayed, route
                context_name = block.locator("xpath=..").get_attribute(
                    "data-xcsh-context"
                )
                if context_name == "shell":
                    syntax = subprocess.run(
                        ["/bin/bash", "-n"],
                        input=copied,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    assert syntax.returncode == 0, (route, syntax.stderr)
                if context_name == "json":
                    structured = json.loads(copied)
                    assert "TOKEN_SENTINEL" not in copied
                    assert "PASSPHRASE_SENTINEL" not in copied
                    if route in ("wingman/", "wingman/validation/"):
                        assert (
                            structured["metadata"]["labels"]["app"]
                            == "reader-wingman-wingman"
                        )
                        assert (
                            structured["spec"]["containers"][0]["env"][0]["value"]
                            == "reader.example.com"
                        )
                if context_name == "hcl":
                    assert "PASSPHRASE_SENTINEL" not in copied
                    assert "TOKEN_SENTINEL" not in copied
                checks.append(
                    {
                        "width": width,
                        "route": route,
                        "clipboard_sha256": hashlib.sha256(copied.encode()).hexdigest(),
                    }
                )
            if route in ("wingman/", "wingman/validation/"):
                assert (
                    page.locator("#ph-XCSH_WINGMAN_NAME").input_value()
                    == "reader-wingman"
                )
                assert (
                    page.locator("#ph-XCSH_KUBECONFIG_CONTEXT").input_value()
                    == "reader-context"
                )
                rendered = page.locator("[data-xcsh-context]").all_text_contents()
                assert any("reader-wingman" in text for text in rendered)
                assert any("reader-context" in text for text in rendered)
            assert not errors, errors
        visit("xcsh/")
        historical = page.locator('[data-personalize="off"]').text_content()
        assert "certificate-management.f5-sales-demo.com" in historical
        assert sentinel not in historical
        assert "reader.example.com" not in historical
        reader = page.locator(
            '[data-xcsh-fields="XCSH_DOMAINNAME XCSH_CERT_FILE"] pre code'
        ).text_content()
        assert "reader.example.com" in reader
        assert "certificate-management.f5-sales-demo.com" not in reader
        visit("terraform/input-lifecycle/")
        hcl = (
            page.locator('[data-xcsh-context="hcl"]')
            .last.locator("pre code")
            .text_content()
        )
        assert "$${literal}" in hcl
        assert "%%{literal}" in hcl
        page.reload()
        page.locator("#placeholder-form").wait_for(state="attached")
        assert page.locator("#ph-XCSH_NAMESPACE").input_value() == sentinel
        assert (
            page.locator("#ph-XCSH_TLS_INPUT_PASSWORD").input_value()
            == "PASSPHRASE_SENTINEL"
        )
        durable = page.evaluate('localStorage.getItem("f5-docs-values-v1")')
        assert "TOKEN_SENTINEL" not in durable
        assert "PASSPHRASE_SENTINEL" not in durable
        # A fresh tab receives durable settings, with its own empty credential session.
        other = context.new_page()
        other.goto(ROOT)
        other.locator("#placeholder-form").wait_for(state="attached")
        assert other.locator("#ph-XCSH_NAMESPACE").input_value() == sentinel
        assert other.locator("#ph-XCSH_TLS_INPUT_PASSWORD").input_value() == ""
        other.close()
        page.locator(".ph-form-wrapper summary").click()
        page.get_by_role("button", name="Reset shared values", exact=True).click()
        assert page.locator("#ph-XCSH_NAMESPACE").input_value() == "demo-app"
        assert (
            page.locator("#ph-XCSH_TLS_INPUT_PASSWORD").input_value()
            == "PASSPHRASE_SENTINEL"
        )
        page.get_by_role("button", name="Clear credentials", exact=True).click()
        assert page.locator("#ph-XCSH_API_TOKEN").input_value() == ""
        assert page.locator("#ph-XCSH_TLS_INPUT_PASSWORD").input_value() == ""
        visit("xcsh/input-workflows/")
        assert (
            'export XCSH_TLS_INPUT_PASSWORD="${XCSH_TLS_INPUT_PASSWORD-}"'
            in page.locator("pre code").first.text_content()
        )
        for url, digest in downloads.items():
            assert hashlib.sha256(context.request.get(url).body()).hexdigest() == digest
        context.close()
    context = browser.new_context()
    context.add_init_script(
        'Object.defineProperty(window,"localStorage",{get(){throw Error("disabled")}}); Object.defineProperty(window,"sessionStorage",{get(){throw Error("disabled")}});'
    )
    page = context.new_page()
    page.goto(ROOT + "xcsh/input-workflows/")
    page.locator("#placeholder-form").wait_for(state="attached")
    page.locator(".ph-form-wrapper summary").click()
    page.locator("#ph-XCSH_TLS_INPUT_PASSWORD").fill("MEMORY_SENTINEL")
    assert "MEMORY_SENTINEL" in page.locator("pre code").first.text_content()
    page.get_by_role("button", name="Clear credentials", exact=True).click()
    assert "MEMORY_SENTINEL" not in page.locator("pre code").first.text_content()
    context.close()
    browser.close()
    receipt = {
        "desktop_mobile_clipboards": checks,
        "session_credentials": True,
        "reset_clear": True,
        "storage_disabled": True,
        "canonical_downloads_unchanged": True,
        "historical_exclusion": True,
        "shared_fields_across_all_routes": True,
        "copied_shell_syntax": True,
        "structured_json_parsing": True,
    }
    (ARTIFACTS / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    sys.stdout.write(
        f"Browser acceptance passed: {len(checks)} desktop/mobile clipboard comparisons and persistence controls.\n"
    )
