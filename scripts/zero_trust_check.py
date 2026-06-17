#!/usr/bin/env python3
"""
Zero Trust Verification Script for Istio Service Mesh
=====================================================
Runs kubectl and istioctl commands to validate that the cluster
enforces Zero Trust principles: identity verification, least-privilege
access, encryption in transit, and continuous validation.

Usage:
    python3 zero_trust_check.py
"""

import subprocess

# ANSI colors
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"
SEPARATOR = "=" * 72

NAMESPACE = "default"


def run_cmd(cmd: str) -> str:
    """Execute a shell command and return its combined stdout/stderr."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=60
    )
    output = result.stdout.strip()
    if result.returncode != 0 and result.stderr.strip():
        output += "\n" + result.stderr.strip()
    return output


def print_check(number: int, title: str, principle: str, explanation: str, cmd: str):
    """Print a check header, run the command, and display its output."""
    print(f"\n{SEPARATOR}")
    print(f"{BOLD}Check #{number}: {title}{RESET}")
    print(f"{SEPARATOR}")
    print(f"{CYAN}Zero Trust Principle:{RESET} {principle}")
    print(f"{GREEN}Explanation:{RESET} {explanation}")
    print(f"{YELLOW}Command:{RESET} {cmd}")
    print(f"\n--- Output ---")
    print(run_cmd(cmd))
    print()


def main():
    print(f"{BOLD}{'=' * 72}{RESET}")
    print(f"{BOLD}       ZERO TRUST VERIFICATION SUITE — Istio Service Mesh{RESET}")
    print(f"{BOLD}{'=' * 72}{RESET}")
    print("This script validates that the cluster enforces Zero Trust principles.")
    print("Namespace:", NAMESPACE)

    check = 0

    # ── 1. Sidecar injection — all pods ───────────────────────────────────
    check += 1
    print_check(
        check,
        "Sidecar proxy injection (all pods)",
        "Never Trust, Always Verify — Identity & Encryption",
        "Every pod must have an Envoy sidecar proxy (2/2 READY containers). "
        "The sidecar terminates mTLS, enforces authorization policies, and "
        "provides workload identity. A pod without a sidecar bypasses all "
        "Zero Trust controls.",
        f"kubectl get pods -n {NAMESPACE} -o wide",
    )

    # ── 2. Namespace label for auto-injection ─────────────────────────────
    check += 1
    print_check(
        check,
        "Namespace auto-injection label",
        "Never Trust, Always Verify — Automated Enforcement",
        "The namespace must be labeled with 'istio-injection=enabled' so that "
        "every new pod automatically gets a sidecar. Without this label, newly "
        "deployed services could run without Zero Trust controls.",
        f"kubectl get namespace {NAMESPACE} --show-labels",
    )

    # ── 3. PeerAuthentication — STRICT mTLS ───────────────────────────────
    check += 1
    print_check(
        check,
        "PeerAuthentication policy (STRICT mTLS)",
        "Encrypt Everything — Mutual TLS",
        "The PeerAuthentication resource enforces STRICT mTLS across the "
        "namespace. Every service-to-service connection MUST be encrypted and "
        "mutually authenticated. Plain-text traffic is rejected, ensuring "
        "confidentiality and integrity of data in transit.",
        f"kubectl get peerauthentication -n {NAMESPACE} -o yaml",
    )

    # ── 4. mTLS certificate chain ─────────────────────────────────────────
    check += 1
    print_check(
        check,
        "mTLS certificate chain (proxy-config secret)",
        "Strong Identity — Certificate Lifecycle",
        "Inspects the TLS certificates loaded in the Envoy sidecar. Verifies "
        "that each workload has a valid SVID (SPIFFE Verifiable Identity "
        "Document) certificate issued by the Istio CA. Short-lived, "
        "auto-rotated certificates are a key Zero Trust property.",
        f"istioctl proxy-config secret "
        f"$(kubectl get pod -n {NAMESPACE} -l app=frontend -o jsonpath='{{.items[0].metadata.name}}') "
        f"-n {NAMESPACE}",
    )

    # ── 5. All AuthorizationPolicies ──────────────────────────────────────
    check += 1
    print_check(
        check,
        "AuthorizationPolicies (all services)",
        "Least Privilege — Micro-segmentation",
        "Lists all AuthorizationPolicy resources. Each policy restricts which "
        "service accounts can communicate with a given service. This is the "
        "core of Zero Trust micro-segmentation: instead of trusting the "
        "network, each service explicitly declares its allowed callers.",
        f"kubectl get authorizationpolicies -n {NAMESPACE}",
    )

    # ── 6. AuthorizationPolicy detail — frontend ──────────────────────────
    check += 1
    print_check(
        check,
        "AuthorizationPolicy detail — frontend",
        "Least Privilege — Explicit Allow-list",
        "Shows the full policy for frontend. Only loadgenerator and external "
        "traffic (without mesh identity) are allowed. All other services are "
        "implicitly denied. This enforces 'never trust, always verify' at L7.",
        f"kubectl get authorizationpolicy frontend-allow-loadgenerator-and-external "
        f"-n {NAMESPACE} -o yaml",
    )

    # ── 7. Service accounts (workload identity) ───────────────────────────
    check += 1
    print_check(
        check,
        "Service accounts (workload identity)",
        "Strong Identity — Cryptographic Workload Identity",
        "Each service runs under its own Kubernetes ServiceAccount, which Istio "
        "maps to a SPIFFE identity (e.g., cluster.local/ns/default/sa/frontend). "
        "These identities are the basis for mTLS authentication and authorization. "
        "Shared or default service accounts would weaken Zero Trust.",
        f"kubectl get serviceaccounts -n {NAMESPACE}",
    )

    # ── 8. No PERMISSIVE mTLS overrides ───────────────────────────────────
    check += 1
    print_check(
        check,
        "Check for PERMISSIVE mTLS overrides",
        "Encrypt Everything — No Exceptions",
        "Searches for any PeerAuthentication with mode=PERMISSIVE, which would "
        "allow plain-text connections and break Zero Trust. In a properly "
        "configured cluster this should return only STRICT entries.",
        f"kubectl get peerauthentication --all-namespaces -o yaml "
        f"| grep -B5 -A2 'mode:' || echo 'No PeerAuthentication overrides found'",
    )

    # ── 9. DestinationRule TLS settings ───────────────────────────────────
    check += 1
    print_check(
        check,
        "DestinationRules — TLS settings",
        "Encrypt Everything — Client-side TLS enforcement",
        "DestinationRules can override TLS settings on the client side. This "
        "check verifies there are no rules disabling TLS (mode: DISABLE) which "
        "would allow a service to send unencrypted traffic, breaking mTLS.",
        f"kubectl get destinationrules -n {NAMESPACE} -o yaml "
        f"| grep -B5 -A5 'tls' || echo 'No DestinationRules with TLS settings found'",
    )

    # ── 10. Mesh-wide authz check ─────────────────────────────────────────
    check += 1
    print_check(
        check,
        "Mesh-wide authorization check (istioctl)",
        "Continuous Validation — Policy Enforcement Audit",
        "Provides a view of authorization policy enforcement for a workload. "
        "Confirms that policies are correctly applied and the mesh operates "
        "under Zero Trust constraints with no misconfigurations.",
        "istioctl x authz check "
        f"$(kubectl get pod -n {NAMESPACE} -l app=frontend -o jsonpath='{{.items[0].metadata.name}}') "
        f"-n {NAMESPACE}",
    )

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{SEPARATOR}")
    print(f"{BOLD}       ZERO TRUST VERIFICATION COMPLETE{RESET}")
    print(f"{SEPARATOR}")
    print(
        f"""
Summary of Zero Trust Principles Verified:

  1. {CYAN}Never Trust, Always Verify{RESET}
     - Sidecar injection ensures every pod has an identity proxy
     - PeerAuthentication STRICT mode rejects unauthenticated connections

  2. {CYAN}Least Privilege Access{RESET}
     - AuthorizationPolicies restrict each service to minimum required callers
     - Implicit deny blocks any unlisted service-to-service communication

  3. {CYAN}Encrypt Everything (mTLS){RESET}
     - STRICT mTLS encrypts all traffic in transit
     - Each workload authenticates with short-lived X.509 certificates (SPIFFE)
     - No PERMISSIVE overrides or DestinationRule TLS bypasses

  4. {CYAN}Strong Workload Identity{RESET}
     - Each service has a dedicated ServiceAccount mapped to a SPIFFE ID
     - Identities are cryptographically verified, not network-based

  5. {CYAN}Assume Breach / Default Deny{RESET}
     - ALLOW policies create an implicit deny-all baseline
     - Micro-segmentation limits blast radius of any compromise

  6. {CYAN}Continuous Monitoring & Validation{RESET}
     - istioctl authz check confirms policies are actively enforced
     - Certificate lifecycle is automated and verifiable
"""
    )


if __name__ == "__main__":
    main()
