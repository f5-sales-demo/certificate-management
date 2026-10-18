# /// script
# dependencies = ["python-hcl2==7.3.1"]
# ///
"""Generate examples from HCL and schemas; Terraform and Biome must be on PATH."""

import argparse
import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import hcl2
from generate_client_mtls import generate as generate_client

ROOT = Path(__file__).resolve().parents[1]


def public_json(value: Any) -> str:
    """Use the repository formatter for generated public configuration downloads."""
    return subprocess.run(
        [  # noqa: S607 -- Fixed repository formatter.
            "biome",
            "format",
            "--stdin-file-path=docs/assets/configurations/generated.json",
        ],
        input=json.dumps(value, indent=2),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout


CHOICES = {
    "advertise-tls": "Advertise TLS",
    "cdn-origin-mtls": "CDN origin mTLS",
    "cdn-server-tls": "CDN server TLS",
    "cluster-tls": "Cluster TLS",
    "http-origin-mtls": "Default pool mTLS",
    "inline-server-tls": "Inline server TLS",
    "origin-mtls": "Origin mTLS",
    "proxy-intercept": "TLS interception",
    "proxy-tls": "Proxy TLS",
    "secret-access-tls": "Secret access TLS",
    "tcp-tls": "TCP TLS",
    "virtual-host-tls": "Virtual host TLS",
    "workload-service-custom": "Custom workload TLS",
    "workload-service-public-multi": "Multiport workload TLS",
    "workload-service-public-single": "Workload TLS",
}
FIELDS = {
    "namespace": "XCSH_NAMESPACE",
    "name": "XCSH_LB_NAME",
    "domain": "XCSH_DOMAINNAME",
    "certificate_file": "XCSH_CERT_FILE",
    "private_key_file": "XCSH_KEY_FILE",
    "origin_hostname": "XCSH_ORIGIN_HOSTNAME",
    "origin_ca_file": "XCSH_ORIGIN_CA_FILE",
    "image": "XCSH_CONTAINER_IMAGE",
    "virtual_site_name": "XCSH_VIRTUAL_SITE_NAME",
    "virtual_site_namespace": "XCSH_VIRTUAL_SITE_NAMESPACE",
}
KINDS = {
    "xcsh_certificate": "certificates",
    "xcsh_http_loadbalancer": "http_loadbalancers",
    "xcsh_origin_pool": "origin_pools",
    "xcsh_advertise_policy": "advertise_policys",
    "xcsh_cluster": "clusters",
    "xcsh_cdn_loadbalancer": "cdn_loadbalancers",
    "xcsh_proxy": "proxys",
    "xcsh_secret_management_access": "secret_management_accesss",
    "xcsh_tcp_loadbalancer": "tcp_loadbalancers",
    "xcsh_virtual_host": "virtual_hosts",
    "xcsh_workload": "workloads",
}


def fence(language: str, content: str) -> str:
    """Annotate each block with its complete shared-field dependency set."""
    context = "shell" if language == "bash" else language
    fields = " ".join(sorted(set(re.findall(r"\bXCSH_[A-Z0-9_]+\b", content))))
    return f'<div data-xcsh-context="{context}" data-xcsh-fields="{fields}">\n\n```{language}\n{content.rstrip()}\n```\n\n</div>\n'


def value(text: Any) -> Any:
    """Resolve only known example expressions; unknown expressions fail generation."""
    if not isinstance(text, str):
        return text
    examples: dict[str, Any] = {
        "${var.origin_sni == null ? var.origin_hostname : var.origin_sni}": "<XCSH_ORIGIN_HOSTNAME>",
        "${var.send_client_certificate ? null : {}}": None,
        "${var.origin_port}": 8080,
        "${var.serve ? null : {}}": {},
        "${var.serve ? {} : null}": None,
        "${var.serve ? True : null}": None,
    }
    examples["${var.client_mtls == null ? {} : null}"] = {}
    if text in examples:
        return examples[text]
    if "base64encode(jsonencode(" in text:
        body = json.dumps(
            {"example": "terraform-certificate", "native_blindfold": True},
            separators=(",", ":"),
        )
        return "string:///" + base64.b64encode(body.encode()).decode()
    text = text.replace("${data.xcsh_namespace.existing.name}", "<XCSH_NAMESPACE>")
    text = text.replace("${xcsh_certificate.server.name}", "<XCSH_LB_NAME>")
    text = text.replace("${xcsh_origin_pool.backend.name}", "<XCSH_LB_NAME>-origin")
    text = text.replace("${filebase64(var.origin_ca_file)}", "<BASE64_ORIGIN_CA>")
    text = text.replace("${origin_servers.value}", "<XCSH_ORIGIN_HOSTNAME>")
    for name, field in FIELDS.items():
        text = text.replace("${var." + name + "}", "<" + field + ">")
    text = text.replace(
        "${var.description}", "Native Terraform Blindfold certificate example"
    )
    if "${" in text:
        raise ValueError("Unsupported expression: " + text)
    return text


def public_dynamic(dynamic: dict, shape: dict) -> dict:
    """Render canonical default branches and reject unsupported dynamic blocks."""
    result: dict[str, Any] = {}
    for name, definition in dynamic.items():
        if "var.client_mtls" in str(definition.get("for_each", "")):
            continue
        if name == "active_service_policies":
            continue
        if name == "tls_certificates":
            result[name] = [
                {
                    "certificate_url": "string:///<BASE64_PUBLIC_CHAIN>",
                    "private_key": {
                        "blindfold_secret_info": {
                            "location": "string:///<ENCRYPTED_KEY>"
                        }
                    },
                }
            ]
        elif name in {"http", "use_mtls"}:
            result[name] = public(
                definition["content"][0], shape["block_types"][name]["block"]
            )
        elif name == "origin_servers":
            content = definition["content"][0]
            if "public_name" in content:
                result[name] = [public(content, shape["block_types"][name]["block"])]
        elif name not in {"routes", "https"}:
            raise ValueError("Unsupported dynamic block " + name)
    return result


def public(body: dict, shape: dict) -> dict:
    """Convert Terraform single/list nesting to the public API configuration."""
    result: dict[str, Any] = {}
    for key, item in body.items():
        if key in {"depends_on", "lifecycle", "timeouts"}:
            continue
        if key == "dynamic":
            for dynamic in item:
                result.update(public_dynamic(dynamic, shape))
            continue
        if key == "blindfold":
            result.update(
                certificate_url="string:///<BASE64_PUBLIC_CHAIN>",
                private_key={
                    "blindfold_secret_info": {"location": "string:///<ENCRYPTED_KEY>"}
                },
            )
            continue
        if key in shape.get("block_types", {}):
            nested = shape["block_types"][key]
            converted = [public(child, nested["block"]) for child in item]
            result[key] = (
                converted[0] if nested["nesting_mode"] == "single" else converted
            )
        elif isinstance(item, dict):
            result[key] = {k: value(v) for k, v in item.items()}
        elif isinstance(item, list):
            result[key] = [value(v) for v in item]
        else:
            resolved = value(item)
            if resolved is not None:
                result[key] = resolved
    return result


def requirements(name: str) -> str:
    """Describe prerequisite-bound serving requirements for each configuration."""
    if "intercept" in name:
        return "Supply a signing CA and matching key, a forward-proxy route, and client trust. Use the interception CA fields rather than a server leaf. Configuration verification does not qualify intercepted traffic."
    if "mtls" in name:
        return "Supply a reachable origin that requires client authentication, a matching client certificate with `clientAuth` usage, and its public server trust CA. Server-only certificates cannot authenticate a client. For callers presenting certificates to the frontend, see [Client mTLS](../../../client-mtls/)."
    if name.startswith("workload"):
        return "Supply an existing CE virtual site with workload capacity and an available container image listening on the target port. An empty selector cannot establish running workload traffic."
    if name == "inline-server-tls":
        return "Supply a tenant-owned hostname with an existing DNS route. Keep each logical certificate's stable ID attached to its material."
    if name == "cdn-server-tls":
        return "Supply a reachable origin and an advertised CDN hostname. The CDN configuration requires an origin even when testing server TLS."
    return "Supply an existing namespace, matching certificate/key files, and a separately owned resource name. Attach a concrete consumer and advertisement before checking served traffic."


def generate(schema: dict) -> None:
    """Generate complete configurations and independent reproducible procedures."""
    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    for name in ["named-certificate", *CHOICES]:
        directory = ROOT / "terraform" / name
        with (directory / "main.tf").open() as stream:
            config = hcl2.load(stream)
        with (directory / "variables.tf").open() as stream:
            variables = hcl2.load(stream)
        documents, reads = [], []
        for resource in config["resource"]:
            for kind, instances in resource.items():
                for label, body in instances.items():
                    converted = public(body, schema[kind]["block"])
                    if name == "http-origin-mtls":
                        converted["default_pool"]["port"] = 443
                    metadata = {
                        key: converted.pop(key)
                        for key in ["name", "namespace", "description", "labels"]
                        if key in converted
                    }
                    documents.append({"metadata": metadata, "spec": converted})
                    suffix = (
                        "-http"
                        if name == "named-certificate" and label == "http"
                        else "-origin"
                        if name == "tcp-tls" and label == "backend"
                        else ""
                    )
                    reads.append(
                        f'curl --silent --show-error --fail --header "Authorization: APIToken $XCSH_API_TOKEN" \\\n  "$XCSH_API_URL/api/config/namespaces/$XCSH_NAMESPACE/{KINDS[kind]}/$TF_VAR_name{suffix}?response_format=2" \\\n  --output "$configuration/{label}-readback.json"'
                    )
        artifact = ROOT / "docs/assets/configurations" / (name + ".json")
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(public_json(documents))
        hcl = "\n".join(p.read_text().rstrip() for p in sorted(directory.glob("*.tf")))
        commands = [
            "umask 077",
            f'configuration="$XCSH_WORKDIR/{name}"',
            'mkdir -p "$configuration"',
        ]
        declared = [key for entry in variables.get("variable", []) for key in entry]
        for key in declared:
            if key in FIELDS:
                field = FIELDS[key]
                if name == "proxy-intercept" and key in [
                    "certificate_file",
                    "private_key_file",
                ]:
                    field = (
                        "XCSH_INTERCEPTION_CA_FILE"
                        if key == "certificate_file"
                        else "XCSH_INTERCEPTION_KEY_FILE"
                    )
                if name == "origin-mtls" and key == "name":
                    field = "XCSH_ORIGIN_POOL_NAME"
                commands.append(f'export TF_VAR_{key}="${field}"')
        if "certificates" in declared:
            commands += [
                'TF_VAR_certificates="$(python3 -c \'import json,os; print(json.dumps([{"id":os.environ["XCSH_CERT_ID"],"certificate_file":os.environ["XCSH_CERT_FILE"],"private_key_file":os.environ["XCSH_KEY_FILE"]}]))\')"',
                "export TF_VAR_certificates",
            ]
        commands += [
            "for file in "
            + " ".join(p.name for p in sorted(directory.glob("*.tf")))
            + "; do",
            f'  curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/{name}/$file" --output "$configuration/$file"',
            "done",
        ]
        if name == "named-certificate":
            dependency = ROOT / "terraform/http-origin-mtls"
            commands += [
                'mkdir -p "$configuration/../http-origin-mtls"',
                "for file in "
                + " ".join(p.name for p in sorted(dependency.glob("*.tf")))
                + "; do",
                '  curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/http-origin-mtls/$file" --output "$configuration/../http-origin-mtls/$file"',
                "done",
            ]
        commands += [
            'terraform -chdir="$configuration" init -upgrade',
            'terraform -chdir="$configuration" validate',
            'terraform -chdir="$configuration" plan -out=create.plan',
            'terraform -chdir="$configuration" show create.plan',
            'shasum -a 256 "$configuration/create.plan"',
        ]
        section = (
            "The JSON below shows the complete public configuration resulting from native encryption, with encoded public chains and encrypted-key placeholders. API defaults and provider provenance may add fields. Never apply encoded-material placeholders. HCL includes the complete canonical root; download its files separately.\n\n"
            f"[Download JSON]({'../../../../assets/' if name != 'named-certificate' else '../../../assets/'}configurations/{name}.json).\n\n"
            "Download HCL files: "
            + " · ".join(
                f"[{path.name}]({'../../../../' if name != 'named-certificate' else '../../../'}_data/terraform/{name}/{path.name})"
                for path in sorted(directory.glob("*.tf"))
            )
            + ".\n\n"
            + (
                "## Public JSON\n\n"
                if name == "named-certificate"
                else "### Public JSON\n\n"
            )
            + fence("json", public_json(documents))
            + "\n"
            + (
                "## Complete HCL\n\n"
                if name == "named-certificate"
                else "### Complete HCL\n\n"
            )
            + fence("hcl", hcl)
        )
        if name == "named-certificate":
            page = ROOT / "docs/en/terraform/configuration.md"
            text = page.read_text()
            begin, end = (
                "<!-- generated-configuration -->",
                "<!-- /generated-configuration -->",
            )
            generated = begin + "\n" + section + "\n" + end
            if begin in text:

                def replacement(_match: re.Match[str], content: str = generated) -> str:
                    return content

                text = re.sub(
                    begin + r"[\s\S]*?" + end,
                    replacement,
                    text,
                )
            else:
                start = text.index("## Complete HCL") + len("## Complete HCL")
                text = text[:start] + "\n\n" + generated + text[start:]
            page.write_text(text)
            continue
        output = ROOT / "docs/en/terraform/certificate-surfaces" / (name + ".md")
        output.parent.mkdir(parents=True, exist_ok=True)
        verify = (
            "\n".join(reads)
            + '\nterraform -chdir="$configuration" plan -detailed-exitcode'
        )
        text = (
            f"---\ntitle: {CHOICES[name]}\nsidebar:\n  order: {list(CHOICES).index(name) + 1}\n---\n\n## Prerequisites\n\nInstall the latest Terraform and provider releases. Set the [provider environment](../../prerequisites/) and keep private inputs and state outside Git. Copy this configuration into its own directory and state; never reuse another owner's name.\n\n{requirements(name)}\n\n## Configuration\n\n{section}\n## Configure\n\nSupply the prerequisite fields in Customize examples. Download the files and review the saved plan.\n\n"
            + fence("bash", "\n".join(commands))
            + "\nConfirm the resource names, references, and ownership in the plan. Apply that reviewed plan.\n\n"
            + fence("bash", 'terraform -chdir="$configuration" apply create.plan')
            + "\nExpect the configured resource to be created with encrypted key material. A failed or uncertain apply requires named readback before recovery; create a fresh plan after reconciling state.\n\n## Verify\n\nRead the complete API configuration privately and check the new process's Terraform plan.\n\n"
            + fence("bash", verify)
            + "\nExpect HTTP `200`, the selected names and references, the encoded public chain, and `private_key.blindfold_secret_info.location` at every certificate node. No `blindfold` input or clear private key belongs in the API object. Expect exit `0` and **No changes**; exit `2` means changes and exit `1` means failure.\n\nConfiguration readback does not prove served TLS. "
        )
        if name == "inline-server-tls":
            text += "Run the [hostname, trust, fingerprint, and response checks](../../verify/). Expect the identifying JSON response.\n"
        elif "mtls" in name:
            text += "Send a request through the configured consumer to the origin. Require trusted server TLS and an origin result confirming the configured client identity; a successful handshake from your laptop does not prove consumer mTLS.\n"
        elif name == "proxy-intercept":
            text += "Use the advertised forward proxy from an authorized client trusting the signing CA. Verify the target hostname and the substituted leaf issuer, then verify the expected application response. This path has no served-traffic qualification receipt.\n"
        else:
            text += "Use the advertised consumer hostname for [trusted TLS checks](../../verify/), then require its application's expected response. Serving remains unqualified until a concrete consumer, advertisement, and traffic check are available.\n"
        if name == "proxy-intercept":
            traffic = (
                'read -r -p "Advertised proxy host:port: " proxy_address\n'
                'openssl s_client -proxy "$proxy_address" -connect "$XCSH_ORIGIN_HOSTNAME:443" '
                '-servername "$XCSH_ORIGIN_HOSTNAME" -verify_hostname "$XCSH_ORIGIN_HOSTNAME" '
                '-verify_return_error -CAfile "$XCSH_INTERCEPTION_CA_FILE" -showcerts < /dev/null '
                '> "$configuration/intercepted-handshake.pem"\n'
                'openssl x509 -in "$configuration/intercepted-handshake.pem" -noout -subject -issuer\n'
                'curl --silent --show-error --fail --proxy "http://$proxy_address" '
                '--cacert "$XCSH_INTERCEPTION_CA_FILE" "https://$XCSH_ORIGIN_HOSTNAME/" '
                '--output "$configuration/intercepted-response"'
            )
            text += "\nAfter configuring an authorized proxy route, inspect its substituted leaf and application response. Require the target hostname and your signing CA's issuer.\n\n"
        elif "mtls" in name:
            traffic = (
                'curl --silent --show-error --fail "https://$XCSH_DOMAINNAME/get" '
                "--output \"$configuration/consumer-response\" --write-out '%{http_code}\\n'"
            )
            text += "\nAfter attaching this configuration to an HTTPS consumer whose certificate chains to your client trust store, request it without supplying your mTLS key from the client. Expect the application's response and separately confirm the origin observed the configured client identity.\n\n"
        else:
            traffic = (
                'openssl s_client -connect "$XCSH_DOMAINNAME:443" -servername "$XCSH_DOMAINNAME" '
                '-verify_hostname "$XCSH_DOMAINNAME" -verify_return_error -CAfile "$XCSH_CERT_FILE" '
                '-showcerts < /dev/null > "$configuration/served-handshake.pem"\n'
                'openssl x509 -in "$XCSH_CERT_FILE" -noout -sha256 -fingerprint > "$configuration/expected-fingerprint"\n'
                'openssl x509 -in "$configuration/served-handshake.pem" -noout -sha256 -fingerprint > "$configuration/served-fingerprint"\n'
                'cmp "$configuration/expected-fingerprint" "$configuration/served-fingerprint"\n'
                'curl --silent --show-error --fail --cacert "$XCSH_CERT_FILE" "https://$XCSH_DOMAINNAME/get" '
                "--output \"$configuration/consumer-response\" --write-out '%{http_code}\\n'"
            )
            text += "\nRun these checks only after attaching an advertised HTTPS consumer on port 443 with this certificate. Expect trusted hostname verification, identical fingerprints, and the application's expected status and response. A different protocol or port requires the corresponding consumer check.\n\n"
        text += fence("bash", traffic)
        text += (
            "\n## Maintain\n\nUse [input and lifecycle guidance](../../input-lifecycle/) for renewal, stable IDs, import, and recovery. Change both private files together, preserve the logical ID and referenced algorithm, review a fresh plan, apply, and repeat configuration and traffic verification.\n\n## Remove\n\nReview and hash a destroy plan for this state. Remove dependent consumers first; the existing namespace is a data source.\n\n"
            + fence(
                "bash",
                'terraform -chdir="$configuration" plan -destroy -out=remove.plan\nterraform -chdir="$configuration" show remove.plan\nshasum -a 256 "$configuration/remove.plan"\nterraform -chdir="$configuration" apply remove.plan\nterraform -chdir="$configuration" state list',
            )
            + "\nExpect only this state's resources to be removed and an empty resource list. Confirm typed API absence; authentication and transport failures do not establish absence.\n"
        )
        output.write_text(text)


def generate_inputs() -> None:
    """Publish complete certificate input roots from the named-certificate source."""
    # pylint: disable=too-many-locals
    base = ROOT / "terraform/named-certificate"
    certificate = (
        (base / "main.tf").read_text().split('resource "xcsh_http_loadbalancer"')[0]
    )
    variants = {
        "protected-pem": (
            "Protected PEM",
            '{ certificate_file = var.certificate_file, private_key_file = var.private_key_file, passphrase_env = "XCSH_TLS_INPUT_PASSWORD" }',
            'export TF_VAR_certificate_file="$XCSH_CERT_FILE"\nexport TF_VAR_private_key_file="$XCSH_PROTECTED_KEY_FILE"',
            "",
        ),
        "pkcs12": (
            "PKCS#12",
            '{ pkcs12_file = var.pkcs12_file, passphrase_env = "XCSH_TLS_INPUT_PASSWORD" }',
            'export TF_VAR_pkcs12_file="$XCSH_P12_FILE"',
            'variable "pkcs12_file" {\n  type = string\n}\n',
        ),
        "write-only-pem": (
            "Write-only PEM",
            '{ certificate_file = var.certificate_file, private_key_wo = var.private_key, material_version = "1" }',
            'export TF_VAR_certificate_file="$XCSH_CERT_FILE"\nTF_VAR_private_key="$(cat "$XCSH_KEY_FILE")"\nexport TF_VAR_private_key\nexport XCSH_MATERIAL_VERSION',
            'variable "private_key" {\n  type = string\n  sensitive = true\n  ephemeral = true\n}\nvariable "material_version" {\n  type = string\n}\n',
        ),
        "write-only-pkcs12": (
            "Write-only PKCS#12",
            '{ pkcs12_wo = var.pkcs12_base64, passphrase_wo = var.passphrase, material_version = "1" }',
            'TF_VAR_pkcs12_base64="$(openssl base64 -A -in "$XCSH_P12_FILE")"\nexport TF_VAR_pkcs12_base64\nexport TF_VAR_passphrase="$XCSH_TLS_INPUT_PASSWORD"\nexport XCSH_MATERIAL_VERSION',
            'variable "pkcs12_base64" {\n  type = string\n  sensitive = true\n  ephemeral = true\n}\nvariable "passphrase" {\n  type = string\n  sensitive = true\n  ephemeral = true\n}\nvariable "material_version" {\n  type = string\n}\n',
        ),
    }
    sections = []
    for name, (title, blindfold, exports, extra) in variants.items():
        directory = ROOT / "terraform/input-variants" / name
        directory.mkdir(parents=True, exist_ok=True)
        main = re.sub(
            r"blindfold\s*=\s*\{[^}]*\}", "blindfold = " + blindfold, certificate
        )
        variables = (base / "variables.tf").read_text()
        # Keep only the certificate variables; HTTPS and route integration remain separately owned.
        variables = re.sub(r'variable "domain" \{[\s\S]*?\n\}', "", variables)
        for selector in ["certificate_file", "private_key_file"]:
            if selector not in blindfold:
                variables = re.sub(
                    r'variable "' + selector + r'" \{[\s\S]*?\n\}', "", variables
                )
        data = '\ndata "xcsh_namespace" "existing" {\n  name = var.namespace\n}\n'
        if 'data "xcsh_namespace"' not in variables:
            variables += data
        extra_variables = re.sub(
            r'variable "material_version" \{[\s\S]*?\n\}', "", extra
        )
        files = {
            "main.tf": main,
            "variables.tf": variables + extra_variables,
            "versions.tf": (base / "versions.tf").read_text(),
        }
        for filename, content in files.items():
            files[filename] = (
                subprocess.run(
                    ["terraform", "fmt", "-"],  # noqa: S607 -- Fixed repository formatter.
                    input=content,
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout.rstrip()
                + "\n"
            )
        for filename, content in files.items():
            (directory / filename).write_text(content)
        setup = (
            'umask 077\nconfiguration="$XCSH_WORKDIR/input-'
            + name
            + '"\nmkdir -p "$configuration"\nexport TF_VAR_namespace="$XCSH_NAMESPACE"\nexport TF_VAR_name="$XCSH_LB_NAME"\n'
        )
        if name != "write-only-pem":
            setup += 'if [ -z "${XCSH_TLS_INPUT_PASSWORD:-}" ]; then\n  printf "Input passphrase: "\n  IFS= read -r -s XCSH_TLS_INPUT_PASSWORD\n  printf "\\n"\nfi\nexport XCSH_TLS_INPUT_PASSWORD\n'
        setup += (
            exports
            + '\nfor file in main.tf variables.tf versions.tf; do\n  curl --silent --show-error --fail "https://f5-sales-demo.github.io/certificate-management/_data/terraform/input-variants/'
            + name
            + '/$file" --output "$configuration/$file"\ndone\nenv -u XCSH_P12_FILE terraform -chdir="$configuration" init -upgrade\nenv -u XCSH_P12_FILE terraform -chdir="$configuration" validate\nenv -u XCSH_P12_FILE terraform -chdir="$configuration" plan -out=input.plan\nenv -u XCSH_P12_FILE terraform -chdir="$configuration" show input.plan\nshasum -a 256 "$configuration/input.plan"'
        )
        if name.startswith("write-only"):
            patch_version = 'python3 -c \'import json,os,re,sys; from pathlib import Path; p=Path(sys.argv[1]); p.write_text(re.sub(r"material_version\\s*=\\s*"+re.escape(json.dumps("1")), lambda _: "material_version = "+json.dumps(os.environ["XCSH_MATERIAL_VERSION"]), p.read_text()))\' "$configuration/main.tf"\n'
            setup = setup.replace(
                'env -u XCSH_P12_FILE terraform -chdir="$configuration" init -upgrade',
                patch_version
                + 'env -u XCSH_P12_FILE terraform -chdir="$configuration" init -upgrade',
            )
        verification = 'env -u XCSH_P12_FILE terraform -chdir="$configuration" apply input.plan\nenv -u XCSH_P12_FILE terraform -chdir="$configuration" plan -detailed-exitcode\ncurl --silent --show-error --fail --header "Authorization: APIToken $XCSH_API_TOKEN" \\\n  "$XCSH_API_URL/api/config/namespaces/$XCSH_NAMESPACE/certificates/$TF_VAR_name?response_format=2" \\\n  --output "$configuration/readback.json"\nunset XCSH_TLS_INPUT_PASSWORD TF_VAR_private_key TF_VAR_pkcs12_base64 TF_VAR_passphrase'
        sections.append(
            "### "
            + title
            + "\n\nUse a separate directory and state, an existing namespace, and an exclusively owned certificate name. This complete HCL owns only the named certificate. Attach it to a separately owned HTTPS consumer for served verification.\n\n"
            + fence("hcl", "\n".join(files.values()))
            + "\nSupply the selected input and review the saved plan.\n\n"
            + fence("bash", setup)
            + "\nApply the reviewed plan and verify encrypted readback.\n\n"
            + fence("bash", verification)
            + "\nExpect HTTP `200`, an encoded public chain, and an encrypted private-key location. Expect **No changes** and exit `0` in a new process. This result does not prove served TLS. Write-only inputs require the same ephemeral values at saved-plan apply and a new material version when inputs change. Keep secrets exported until verification finishes, then unset them.\n"
        )
    page = ROOT / "docs/en/terraform/input-lifecycle.md"
    text = page.read_text()
    start, end = (
        text.index("## Input choices"),
        text.index("## Stable inline identities"),
    )
    introduction = "## Input choices\n\nThe bundle input field `XCSH_P12_FILE` also configures provider authentication. The input commands remove it from the Terraform process environment after copying the bundle path or contents to a dedicated input variable, so API token authentication stays independent.\n\nUse file inputs for unprotected PEM in the [certificate workflow](../). The alternatives below prepare the same public configuration shown there. `sensitive` hides display; only ephemeral write-only variables prevent private inputs from entering plans and state. Never put keys or bundles in ordinary variables.\n\n"
    page.write_text(
        text[:start] + introduction + "\n".join(sections) + "\n" + text[end:]
    )
    imports = ROOT / "docs/_imports"
    lines = imports.read_text().splitlines()
    for name in variants:
        for filename in ["main.tf", "variables.tf", "versions.tf"]:
            path = f"terraform/input-variants/{name}/{filename}"
            line = path + " -> " + path
            if line not in lines:
                lines.append(line)
    imports.write_text("\n".join(lines) + "\n")


def generate_wingman() -> None:
    """Render the Deployment from the canonical Terraform runtime."""
    config = hcl2.loads((ROOT / "wingman/runtime/main.tf").read_text())
    body = next(
        resource["kubernetes_deployment_v1"]["application"]
        for resource in config["resource"]
        if "kubernetes_deployment_v1" in resource
    )
    expressions = {
        "${local.names.application}": "<XCSH_WINGMAN_NAME>-wingman",
        "${local.namespace}": "<XCSH_NAMESPACE>",
        "${local.selector}": {"app": "<XCSH_WINGMAN_NAME>-wingman"},
        'ghcr.io/f5-sales-demo/certificate-management-wingman@sha256:${split(":", data.external.application_image.result.digest)[1]}': "ghcr.io/f5-sales-demo/certificate-management-wingman@sha256:<RESOLVED_IMAGE_DIGEST>",
        "${local.contract.backend_port}": 8443,
        "${var.domain}": "<XCSH_DOMAINNAME>",
        "${sha256(jsonencode(kubernetes_config_map_v1.material.data))}": "<MATERIAL_SHA256>",
        "${kubernetes_config_map_v1.material.metadata[0].name}": "<XCSH_WINGMAN_NAME>-wingman-material",
    }
    arrays = {
        "container": "containers",
        "port": "ports",
        "env": "env",
        "volume_mount": "volumeMounts",
        "volume": "volumes",
    }

    def convert(node: Any) -> Any:
        if isinstance(node, str):
            if node in expressions:
                return expressions[node]
            if "${" in node:
                raise ValueError("Unsupported runtime expression: " + node)
            return node
        if isinstance(node, list):
            return [convert(item) for item in node]
        if not isinstance(node, dict):
            return node
        result = {}
        for key, item in node.items():
            # Labels, annotations, and resource quantities are literal map keys.
            if key in {
                "labels",
                "annotations",
                "requests",
                "limits",
                "match_labels",
            } and isinstance(item, dict):
                converted = {name: convert(value) for name, value in item.items()}
            elif (
                isinstance(item, list)
                and item
                and isinstance(item[0], dict)
                and key not in arrays
            ):
                if len(item) != 1:
                    raise ValueError("Expected one runtime block: " + key)
                converted = convert(item[0])
            else:
                converted = convert(item)
            words = key.split("_")
            name = words[0] + "".join(word.title() for word in words[1:])
            if isinstance(item, list):
                name = arrays.get(key, name)
            result[name] = converted
        return result

    document = {"apiVersion": "apps/v1", "kind": "Deployment", **convert(body)}
    artifact = ROOT / "docs/assets/configurations/wingman-deployment.json"
    artifact.write_text(public_json(document))
    page = ROOT / "docs/en/wingman/configuration.md"
    text = page.read_text()
    text = re.sub(
        r'<div data-xcsh-context="json"[\s\S]*?</div>\n*',
        lambda _: fence("json", public_json(document)) + "\n",
        text,
        count=1,
    )
    marker = "<!-- generated-wingman-hcl -->"
    text = text.split(marker)[0].rstrip()
    sections = []
    for name in ("bootstrap", "runtime", "qualification"):
        directory = ROOT / "wingman" / name
        files = sorted(directory.glob("*.tf"))
        downloads = " · ".join(
            f"[{path.name}](../../../_data/wingman/{name}/{path.name})"
            for path in files
        )
        complete = "\n".join(path.read_text().rstrip() for path in files)
        sections.append(
            f"## {name.capitalize()} HCL\n\nDownload unchanged files: {downloads}.\n\n"
            + fence("hcl", complete)
        )
    page.write_text(text + "\n\n" + marker + "\n\n" + "\n\n".join(sections) + "\n")


def generate_xcsh() -> None:
    """Render the public illustrative manifest from its canonical downloadable source."""
    artifact = ROOT / "docs/assets/configurations/xcsh-certificate.json"
    public_manifest = artifact.read_text()
    json.loads(public_manifest)
    page = ROOT / "docs/en/xcsh/configuration.md"
    page.write_text(
        re.sub(
            r"```json\n[\s\S]*?```",
            lambda _: "```json\n" + public_manifest.rstrip() + "\n```",
            page.read_text(),
            count=1,
        )
    )


def main() -> None:
    """Read the installed schema and generate all supported examples."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, required=True)
    args = parser.parse_args()
    source = args.schema.read_bytes()
    schema = json.loads(source)["provider_schemas"][
        "registry.terraform.io/f5-sales-demo/xcsh"
    ]["resource_schemas"]
    generate(schema)
    generate_inputs()
    generate_wingman()
    generate_xcsh()
    generate_client(schema, public, public_json, fence)
    named_page = ROOT / "docs/en/terraform/configure.md"
    page_text = re.sub(
        r"for file in [^\n]+; do\n(?=[\s\S]{0,300}named-certificate/\$file)",
        lambda _: (
            "for file in "
            + " ".join(
                path.name
                for path in sorted((ROOT / "terraform/named-certificate").glob("*.tf"))
            )
            + "; do\n"
        ),
        named_page.read_text(),
        count=1,
    )
    named_page.write_text(page_text)
    for page in (ROOT / "docs/en").rglob("*.md"):
        page.write_text(re.sub(r"\n{3,}", "\n\n", page.read_text()))
    (ROOT / "verification/administration-source.json").write_text(
        json.dumps(
            {
                "schema_sha256": hashlib.sha256(source).hexdigest(),
                "examples": ["named-certificate", *CHOICES],
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
