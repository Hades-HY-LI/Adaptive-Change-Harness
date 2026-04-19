from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from app.models.schemas import RepoProfile
from app.services.shell import ShellRunner


@dataclass
class ProbeSpec:
    probe_id: str
    title: str
    summary: str
    severity: str
    confidence: float
    suspect_files: list[str]
    script_path: str


@dataclass
class ProbeResult:
    probe_id: str
    title: str
    passed: bool
    summary: str
    details: str
    failing_command: str
    reproduction_steps: list[str]
    suspect_files: list[str]
    severity: str
    confidence: float
    script_path: str | None = None
    script_contents: str | None = None


class ProbeRunner:
    def __init__(self, shell_runner: ShellRunner) -> None:
        self.shell_runner = shell_runner

    def run(self, workspace: Path, repo_profile: RepoProfile) -> list[ProbeResult]:
        specs = self._generate_specs(workspace, repo_profile)
        results: list[ProbeResult] = []
        for spec in specs:
            command = self.shell_runner.python_command(spec.script_path)
            result = self.shell_runner.run(command, cwd=workspace)
            details = (result.stdout + "\n" + result.stderr).strip()
            relative_command = f"python {spec.script_path}"
            script_contents = (workspace / spec.script_path).read_text()
            results.append(
                ProbeResult(
                    probe_id=spec.probe_id,
                    title=spec.title,
                    passed=result.exit_code == 0,
                    summary=spec.summary if result.exit_code != 0 else f"{spec.title} passed.",
                    details=details,
                    failing_command=relative_command,
                    reproduction_steps=[relative_command],
                    suspect_files=spec.suspect_files,
                    severity=spec.severity,
                    confidence=spec.confidence,
                    script_path=spec.script_path,
                    script_contents=script_contents,
                )
            )
        return results

    def _generate_specs(self, workspace: Path, repo_profile: RepoProfile) -> list[ProbeSpec]:
        if repo_profile.framework != "fastapi":
            return []

        route_paths = self._detect_route_paths(workspace, repo_profile)
        pricing_file = self._find_first(workspace, ("*pricing*.py",))
        checkout_file = self._find_first(workspace, ("*checkout*.py",))
        subscription_file = self._find_first(workspace, ("*subscription*.py",))
        repository_file = self._find_first(workspace, ("*repository*.py",))
        entrypoint = self._resolve_entrypoint(repo_profile)

        plans = self._extract_quoted_values(workspace, pricing_file, ("starter", "pro", "enterprise")) if pricing_file else ["starter"]
        discount_codes = self._extract_discount_codes(workspace, pricing_file) if pricing_file else []

        specs: list[ProbeSpec] = []
        probe_dir = workspace / ".harness" / "probes"
        probe_dir.mkdir(parents=True, exist_ok=True)

        if entrypoint and pricing_file and "/quote" in route_paths and discount_codes:
            script_path = probe_dir / "negative_total_quote_probe.py"
            script_path.write_text(self._negative_total_quote_script(entrypoint, plans, discount_codes))
            specs.append(
                ProbeSpec(
                    probe_id="negative_total_quote",
                    title="Negative total quote probe",
                    summary="Detected a quote request that returns a negative total.",
                    severity="high",
                    confidence=0.95,
                    suspect_files=[pricing_file],
                    script_path=".harness/probes/negative_total_quote_probe.py",
                )
            )

        if entrypoint and checkout_file and "/checkout" in route_paths and discount_codes:
            script_path = probe_dir / "checkout_optional_metadata_probe.py"
            script_path.write_text(self._checkout_optional_metadata_script(entrypoint, plans, discount_codes))
            specs.append(
                ProbeSpec(
                    probe_id="checkout_optional_metadata",
                    title="Checkout optional metadata probe",
                    summary="Detected a checkout crash when optional metadata is omitted.",
                    severity="high",
                    confidence=0.93,
                    suspect_files=[checkout_file],
                    script_path=".harness/probes/checkout_optional_metadata_probe.py",
                )
            )

        if checkout_file and repository_file:
            script_path = probe_dir / "idempotency_retry_probe.py"
            script_path.write_text(self._idempotency_retry_script())
            specs.append(
                ProbeSpec(
                    probe_id="idempotency_retry_duplicate_charge",
                    title="Idempotency retry duplicate charge probe",
                    summary="Detected duplicate charges across timeout retries with the same idempotency key.",
                    severity="high",
                    confidence=0.96,
                    suspect_files=[checkout_file, repository_file],
                    script_path=".harness/probes/idempotency_retry_probe.py",
                )
            )

        if entrypoint and subscription_file and "/subscriptions/{subscription_id}" in route_paths:
            script_path = probe_dir / "subscription_contract_probe.py"
            script_path.write_text(self._subscription_contract_script(entrypoint))
            specs.append(
                ProbeSpec(
                    probe_id="subscription_contract_mismatch",
                    title="Subscription response contract probe",
                    summary="Detected an inconsistent subscription response shape.",
                    severity="medium",
                    confidence=0.9,
                    suspect_files=[subscription_file],
                    script_path=".harness/probes/subscription_contract_probe.py",
                )
            )

        if subscription_file and repository_file:
            script_path = probe_dir / "fraud_cancel_audit_probe.py"
            script_path.write_text(self._fraud_cancel_audit_script())
            specs.append(
                ProbeSpec(
                    probe_id="fraud_cancel_audit_gap",
                    title="Fraud cancellation audit probe",
                    summary="Detected a cancellation path that bypasses audit logging.",
                    severity="medium",
                    confidence=0.88,
                    suspect_files=[subscription_file, repository_file],
                    script_path=".harness/probes/fraud_cancel_audit_probe.py",
                )
            )

        return specs

    def _detect_route_paths(self, workspace: Path, repo_profile: RepoProfile) -> set[str]:
        route_paths: set[str] = set()
        for entrypoint in repo_profile.entrypoints:
            target = workspace / entrypoint
            if not target.exists():
                continue
            try:
                content = target.read_text()
            except UnicodeDecodeError:
                continue
            route_paths.update(match.group(1) for match in re.finditer(r'@app\.(?:get|post|put|delete)\("([^"]+)"', content))
        return route_paths

    def _find_first(self, workspace: Path, patterns: tuple[str, ...]) -> str | None:
        for pattern in patterns:
            matches = sorted(workspace.rglob(pattern))
            if matches:
                return matches[0].relative_to(workspace).as_posix()
        return None

    def _resolve_entrypoint(self, repo_profile: RepoProfile) -> str | None:
        return repo_profile.entrypoints[0] if repo_profile.entrypoints else None

    def _extract_discount_codes(self, workspace: Path, pricing_file: str) -> list[str]:
        target = workspace / pricing_file
        if not target.exists():
            return []
        content = target.read_text()
        codes = re.findall(r'"([A-Z0-9_]{4,})"\s*:', content)
        return sorted(set(codes))

    def _extract_quoted_values(self, workspace: Path, source_file: str, defaults: tuple[str, ...]) -> list[str]:
        target = workspace / source_file
        if not target.exists():
            return list(defaults)
        content = target.read_text()
        matches = re.findall(r'"([a-z][a-z0-9_]+)"\s*:', content)
        values = [value for value in matches if value in defaults]
        return sorted(set(values)) or list(defaults)

    def _negative_total_quote_script(self, entrypoint: str, plans: list[str], discount_codes: list[str]) -> str:
        return f"""{self._script_preamble()}from fastapi.testclient import TestClient
from {self._module_path(entrypoint)} import app

client = TestClient(app)
plans = {plans!r}
discount_codes = {discount_codes!r}
for plan_code in plans:
    for discount_code in discount_codes:
        response = client.post("/quote", json={{"plan_code": plan_code, "seats": 1, "discount_code": discount_code}})
        if response.status_code != 200:
            continue
        payload = response.json()
        total = payload.get("total_cents")
        if isinstance(total, int) and total < 0:
            print(f"negative total detected for plan={{plan_code}} discount={{discount_code}} total={{total}}")
            raise SystemExit(1)
print("no negative total detected")
"""

    def _checkout_optional_metadata_script(self, entrypoint: str, plans: list[str], discount_codes: list[str]) -> str:
        plan_code = plans[0] if plans else "starter"
        return f"""{self._script_preamble()}from fastapi.testclient import TestClient
from {self._module_path(entrypoint)} import app

client = TestClient(app)
discount_codes = {discount_codes!r}
for discount_code in discount_codes:
    response = client.post(
        "/checkout",
        json={{
            "customer_id": "probe_customer",
            "customer_email": "probe@example.com",
            "plan_code": {plan_code!r},
            "discount_code": discount_code
        }},
    )
    if response.status_code >= 500:
        print(f"checkout crashed for discount={{discount_code}} status={{response.status_code}} body={{response.text}}")
        raise SystemExit(1)
print("checkout optional metadata probe passed")
"""

    def _idempotency_retry_script(self) -> str:
        return f"""{self._script_preamble()}from app.models import CheckoutRequest
from app.repository import repository
from app.services.checkout import CheckoutError, create_checkout

repository.reset()
request = CheckoutRequest(
    customer_id="probe_customer",
    customer_email="probe@example.com",
    plan_code="starter",
    idempotency_key="probe-idempotency",
    metadata={{"simulate_timeout": True}},
)
for _ in range(2):
    try:
        create_checkout(request)
    except CheckoutError:
        pass
if len(repository.charges) > 1:
    print(f"duplicate charges detected across retry: charges={{len(repository.charges)}}")
    raise SystemExit(1)
print("idempotency retry probe passed")
"""

    def _subscription_contract_script(self, entrypoint: str) -> str:
        return f"""{self._script_preamble()}from fastapi.testclient import TestClient
from {self._module_path(entrypoint)} import app

client = TestClient(app)
checkout = client.post(
    "/checkout",
    json={{"customer_id": "probe_customer", "customer_email": "probe@example.com", "plan_code": "starter"}},
)
if checkout.status_code != 200:
    raise SystemExit(0)
subscription_id = checkout.json()["subscription_id"]
response = client.get(f"/subscriptions/{{subscription_id}}?include_usage=true")
if response.status_code != 200:
    raise SystemExit(0)
payload = response.json()
if "planCode" in payload or "plan_code" not in payload:
    print(f"inconsistent subscription payload: {{payload}}")
    raise SystemExit(1)
print("subscription contract probe passed")
"""

    def _fraud_cancel_audit_script(self) -> str:
        return f"""{self._script_preamble()}from app.models import CheckoutRequest
from app.repository import repository
from app.services.checkout import create_checkout
from app.services.subscriptions import cancel_subscription

repository.reset()
checkout = create_checkout(
    CheckoutRequest(customer_id="probe_customer", customer_email="probe@example.com", plan_code="starter")
)
cancel_subscription(checkout.subscription_id, "fraud")
audit_events = [item["event_type"] for item in repository.audit_log]
if "subscription_canceled" not in audit_events:
    print(f"missing subscription_canceled audit event: {{audit_events}}")
    raise SystemExit(1)
print("fraud cancel audit probe passed")
"""

    def _module_path(self, entrypoint: str) -> str:
        return entrypoint[:-3].replace("/", ".")

    def _script_preamble(self) -> str:
        return (
            "from pathlib import Path\n"
            "import sys\n\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))\n\n"
        )
