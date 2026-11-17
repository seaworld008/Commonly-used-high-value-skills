#!/usr/bin/env python3
"""
Security Risk Assessment Tool

Offline catalog scenario analysis supporting ISO 27001 risk workshops.
Does not discover assets, scan vulnerabilities, or verify control evidence.

Usage:
    python risk_assessment.py --scope "example" --demo --format json
    python risk_assessment.py --scope "system-name" --assets assets.csv --template healthcare
"""

import argparse
import csv
import io
import json
import math
import sys
import unicodedata
from datetime import datetime
from typing import Dict, List, Any, Optional


# Threat catalogs by template
THREAT_CATALOGS = {
    "general": [
        {"id": "T01", "name": "Unauthorized access", "category": "Access", "likelihood": 4},
        {"id": "T02", "name": "Data breach", "category": "Confidentiality", "likelihood": 3},
        {"id": "T03", "name": "Malware infection", "category": "Integrity", "likelihood": 4},
        {"id": "T04", "name": "Phishing attack", "category": "Social Engineering", "likelihood": 5},
        {"id": "T05", "name": "Denial of service", "category": "Availability", "likelihood": 3},
        {"id": "T06", "name": "Insider threat", "category": "Personnel", "likelihood": 2},
        {"id": "T07", "name": "Physical theft", "category": "Physical", "likelihood": 2},
        {"id": "T08", "name": "System misconfiguration", "category": "Technical", "likelihood": 4},
        {"id": "T09", "name": "Third-party compromise", "category": "Supply Chain", "likelihood": 3},
        {"id": "T10", "name": "Natural disaster", "category": "Environmental", "likelihood": 1},
    ],
    "healthcare": [
        {"id": "T01", "name": "Patient data breach", "category": "Confidentiality", "likelihood": 4},
        {"id": "T02", "name": "Ransomware attack", "category": "Availability", "likelihood": 4},
        {"id": "T03", "name": "Medical device tampering", "category": "Integrity", "likelihood": 3},
        {"id": "T04", "name": "EHR unauthorized access", "category": "Access", "likelihood": 4},
        {"id": "T05", "name": "HIPAA violation", "category": "Compliance", "likelihood": 3},
        {"id": "T06", "name": "Clinical data corruption", "category": "Integrity", "likelihood": 2},
        {"id": "T07", "name": "Telemedicine interception", "category": "Confidentiality", "likelihood": 3},
        {"id": "T08", "name": "Credential theft", "category": "Access", "likelihood": 5},
        {"id": "T09", "name": "Third-party vendor breach", "category": "Supply Chain", "likelihood": 3},
        {"id": "T10", "name": "Insider data theft", "category": "Personnel", "likelihood": 2},
    ],
    "cloud": [
        {"id": "T01", "name": "Cloud misconfiguration", "category": "Technical", "likelihood": 5},
        {"id": "T02", "name": "API vulnerability exploit", "category": "Application", "likelihood": 4},
        {"id": "T03", "name": "Account hijacking", "category": "Access", "likelihood": 4},
        {"id": "T04", "name": "Data exfiltration", "category": "Confidentiality", "likelihood": 3},
        {"id": "T05", "name": "Shared tenancy attack", "category": "Infrastructure", "likelihood": 2},
        {"id": "T06", "name": "Service outage", "category": "Availability", "likelihood": 3},
        {"id": "T07", "name": "Compliance violation", "category": "Compliance", "likelihood": 3},
        {"id": "T08", "name": "Shadow IT exposure", "category": "Governance", "likelihood": 4},
        {"id": "T09", "name": "Encryption key exposure", "category": "Cryptography", "likelihood": 2},
        {"id": "T10", "name": "CSP vendor lock-in", "category": "Strategic", "likelihood": 3},
    ],
}

# Vulnerability patterns
VULNERABILITY_PATTERNS = {
    "access": ["No MFA", "Weak passwords", "Excessive privileges", "Shared accounts"],
    "technical": ["Unpatched systems", "Weak encryption", "Missing logging", "Open ports"],
    "process": ["No incident response", "Missing backups", "No change control", "Lack of monitoring"],
    "people": ["Untrained staff", "No security awareness", "Social engineering susceptibility"],
}

# Asset classification criteria
CLASSIFICATION_CRITERIA = {
    "critical": {"description": "Business-critical, severe impact if compromised", "impact": 5},
    "high": {"description": "Important assets, significant impact", "impact": 4},
    "medium": {"description": "Standard business assets, moderate impact", "impact": 3},
    "low": {"description": "Limited business value, minor impact", "impact": 2},
    "minimal": {"description": "Public or non-sensitive, negligible impact", "impact": 1},
}

# Risk treatment options
TREATMENT_OPTIONS = {
    "critical": "Immediate mitigation required - implement controls within 7 days",
    "high": "Priority mitigation - implement controls within 30 days",
    "medium": "Planned mitigation - implement controls within 90 days",
    "low": "Accept risk with monitoring or implement low-cost controls",
    "minimal": "Accept risk - document acceptance decision",
}


def calculate_risk_score(likelihood: int, impact: int) -> int:
    """Calculate risk score as likelihood × impact."""
    return likelihood * impact


def get_risk_level(score: int) -> str:
    """Determine risk level from score."""
    if score >= 20:
        return "critical"
    elif score >= 15:
        return "high"
    elif score >= 10:
        return "medium"
    elif score >= 5:
        return "low"
    return "minimal"


def validate_csv_headers(reader: csv.DictReader, label: str) -> None:
    """Reject ambiguous columns before DictReader can overwrite row evidence."""
    headers = [unicodedata.normalize("NFKC", name).strip().casefold()
               for name in (reader.fieldnames or [])]
    seen = set()
    for name in headers:
        if not name:
            raise ValueError(f"{label} CSV has an empty column name")
        if name in seen:
            raise ValueError(f"{label} CSV has a duplicate column name: {name}")
        seen.add(name)


def load_assets_from_csv(filepath: str) -> List[Dict[str, Any]]:
    """Load a supplied inventory; never substitute missing data with samples."""
    assets = []
    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        validate_csv_headers(reader, "Asset")
        if not {"id", "name", "classification"}.issubset(reader.fieldnames or []):
            raise ValueError("Asset CSV requires id,name,classification columns")
        seen = set()
        for row in reader:
            asset = {key: (row.get(key) or "").strip()
                     for key in ("id", "name", "type", "owner", "classification")}
            asset["classification"] = asset["classification"].lower()
            if not asset["id"] or not asset["name"] or asset["id"] in seen:
                raise ValueError("Assets require unique nonempty id and nonempty name")
            if asset["classification"] not in CLASSIFICATION_CRITERIA:
                raise ValueError("Unknown asset classification; use critical/high/medium/low/minimal")
            asset["type"] = asset["type"] or "Unspecified"
            asset["owner"] = asset["owner"] or "Unassigned"
            assets.append(asset)
            seen.add(asset["id"])
    if not assets:
        raise ValueError("Asset inventory is empty; use --demo for synthetic examples")
    return assets


def load_control_evidence(filepath: str, assets: List[Dict[str, Any]], template: str) -> Dict:
    """Read supplied attestations, without opening or fetching evidence references.

    Completeness is checked here; authenticity and applicability require review.
    Missing or invalid attestations leave effectiveness unknown.
    """
    controls = {}
    asset_ids = {asset["id"] for asset in assets}
    threat_ids = {threat["id"] for threat in THREAT_CATALOGS[template][:5]}
    with open(filepath, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        validate_csv_headers(reader, "Control evidence")
        required = {"asset_id", "threat_id", "status", "effectiveness",
                    "evidence_ref", "assessed_by", "assessed_at"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Control evidence CSV requires " + ",".join(sorted(required)))
        for row in reader:
            row = {key: (row.get(key) or "").strip() for key in required}
            key = (row["asset_id"], row["threat_id"])
            if key[0] not in asset_ids or key[1] not in threat_ids or key in controls:
                raise ValueError("Control evidence has an unknown or duplicate asset/threat pair")
            row["accepted"] = False
            try:
                effectiveness = float(row["effectiveness"])
                assessed_at = datetime.fromisoformat(row["assessed_at"])
                row["accepted"] = (
                    row["status"].lower() == "verified"
                    and bool(row["evidence_ref"] and row["assessed_by"])
                    and math.isfinite(effectiveness) and 0 <= effectiveness <= 1
                    and assessed_at.date() <= datetime.now().date()
                )
                if row["accepted"]:
                    row["effectiveness"] = effectiveness
            except ValueError:
                pass
            controls[key] = row
    return controls


def generate_sample_assets(scope: str, template: str) -> List[Dict[str, Any]]:
    """Generate sample asset inventory based on scope and template."""
    base_assets = []

    if template == "healthcare":
        base_assets = [
            {"id": "A001", "name": "Patient Database", "type": "Information", "owner": "DBA Team", "classification": "critical"},
            {"id": "A002", "name": "EHR Application", "type": "Software", "owner": "App Team", "classification": "critical"},
            {"id": "A003", "name": "Medical Imaging System", "type": "Software", "owner": "Radiology", "classification": "high"},
            {"id": "A004", "name": "Database Servers", "type": "Hardware", "owner": "Infrastructure", "classification": "high"},
            {"id": "A005", "name": "Admin Credentials", "type": "Access", "owner": "Security", "classification": "critical"},
            {"id": "A006", "name": "Backup Systems", "type": "Service", "owner": "IT Ops", "classification": "high"},
            {"id": "A007", "name": "Network Infrastructure", "type": "Hardware", "owner": "Network Team", "classification": "high"},
            {"id": "A008", "name": "API Gateway", "type": "Software", "owner": "Platform Team", "classification": "high"},
        ]
    elif template == "cloud":
        base_assets = [
            {"id": "A001", "name": "Cloud Storage Buckets", "type": "Service", "owner": "Platform", "classification": "high"},
            {"id": "A002", "name": "Container Registry", "type": "Service", "owner": "DevOps", "classification": "high"},
            {"id": "A003", "name": "API Services", "type": "Software", "owner": "Engineering", "classification": "critical"},
            {"id": "A004", "name": "Database Instances", "type": "Service", "owner": "DBA Team", "classification": "critical"},
            {"id": "A005", "name": "IAM Configuration", "type": "Access", "owner": "Security", "classification": "critical"},
            {"id": "A006", "name": "Secrets Manager", "type": "Service", "owner": "Security", "classification": "critical"},
            {"id": "A007", "name": "Load Balancers", "type": "Infrastructure", "owner": "Platform", "classification": "high"},
            {"id": "A008", "name": "Monitoring Systems", "type": "Service", "owner": "SRE", "classification": "medium"},
        ]
    else:  # general
        base_assets = [
            {"id": "A001", "name": "Corporate Data", "type": "Information", "owner": "Data Team", "classification": "high"},
            {"id": "A002", "name": "Business Applications", "type": "Software", "owner": "IT", "classification": "high"},
            {"id": "A003", "name": "Server Infrastructure", "type": "Hardware", "owner": "Infrastructure", "classification": "high"},
            {"id": "A004", "name": "User Credentials", "type": "Access", "owner": "Security", "classification": "critical"},
            {"id": "A005", "name": "Email System", "type": "Service", "owner": "IT", "classification": "medium"},
            {"id": "A006", "name": "File Servers", "type": "Hardware", "owner": "Infrastructure", "classification": "medium"},
            {"id": "A007", "name": "Network Equipment", "type": "Hardware", "owner": "Network", "classification": "high"},
            {"id": "A008", "name": "Backup Infrastructure", "type": "Service", "owner": "IT Ops", "classification": "high"},
        ]

    # Tag assets with scope
    for asset in base_assets:
        asset["scope"] = scope

    return base_assets


def assess_risks(
    assets: List[Dict[str, Any]],
    template: str
) -> List[Dict[str, Any]]:
    """Expand catalog scenarios, not observations about the supplied assets."""
    threats = THREAT_CATALOGS.get(template, THREAT_CATALOGS["general"])
    risks = []
    risk_id = 1

    for asset in assets:
        classification = asset.get("classification", "medium")
        impact = CLASSIFICATION_CRITERIA.get(classification, {}).get("impact", 3)

        # Map relevant threats to asset
        relevant_threats = threats[:5]  # Top 5 threats for each asset

        for threat in relevant_threats:
            likelihood = threat["likelihood"]
            score = calculate_risk_score(likelihood, impact)
            level = get_risk_level(score)

            # Identify potential vulnerabilities
            vuln_category = threat["category"].lower()
            vulns = VULNERABILITY_PATTERNS.get("technical", ["Unknown vulnerability"])
            if "access" in vuln_category:
                vulns = VULNERABILITY_PATTERNS["access"]
            elif "personnel" in vuln_category or "social" in vuln_category:
                vulns = VULNERABILITY_PATTERNS["people"]

            risk = {
                "id": f"R{risk_id:03d}",
                "asset_id": asset["id"],
                "asset_name": asset["name"],
                "threat_id": threat["id"],
                "threat_name": threat["name"],
                "threat_category": threat["category"],
                "vulnerability": vulns[0] if vulns else "Unidentified",
                "vulnerability_status": "unknown",
                "scenario_source": f"bundled_catalog:{template}",
                "scenario_status": "unverified_catalog_scenario",
                "score_basis": "assumed_catalog_likelihood_x_supplied_classification_impact",
                "likelihood": likelihood,
                "impact": impact,
                "score": score,
                "level": level,
                "treatment": TREATMENT_OPTIONS.get(level, "Review required"),
            }
            risks.append(risk)
            risk_id += 1

    # Sort by risk score descending
    risks.sort(key=lambda x: x["score"], reverse=True)
    return risks


def calculate_residual_risk(risk: Dict[str, Any], evidence: Optional[Dict] = None) -> Dict[str, Any]:
    """Estimate only with complete supplied evidence; catalog scores stay assumed."""
    result = {
        "risk_id": risk["id"],
        "inherent_score": risk["score"],
        "control_status": "unknown",
        "control_effectiveness": None,
        "residual_status": "not_estimable",
        "residual_likelihood": None,
        "residual_score": None,
        "residual_level": None,
        "evidence_ref": evidence.get("evidence_ref") if evidence else None,
        "assessed_by": evidence.get("assessed_by") if evidence else None,
        "assessed_at": evidence.get("assessed_at") if evidence else None,
        "basis": "Missing or incomplete verified control evidence; no effectiveness assumed",
    }
    if evidence and evidence.get("accepted"):
        effectiveness = evidence["effectiveness"]
        likelihood = max(1, math.ceil(risk["likelihood"] * (1 - effectiveness)))
        score = calculate_risk_score(likelihood, risk["impact"])
        result.update({
            "control_status": "reported_verified",
            "control_effectiveness": effectiveness,
            "residual_status": "conditional_estimate",
            "residual_likelihood": likelihood,
            "residual_score": score,
            "residual_level": get_risk_level(score),
            "basis": "Supplied control attestation applied to assumed catalog likelihood; "
                     "evidence authenticity and scenario applicability not independently verified",
        })
    return result


def generate_report(
    scope: str,
    template: str,
    assets: List[Dict[str, Any]],
    risks: List[Dict[str, Any]],
    output_format: str,
    *,
    demo: bool = False,
    asset_source: Optional[str] = None,
    control_source: Optional[str] = None,
    controls: Optional[Dict] = None,
) -> str:
    """Generate risk assessment report."""
    timestamp = datetime.now().isoformat()

    # Calculate summary statistics
    risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "minimal": 0}
    for risk in risks:
        risk_counts[risk["level"]] += 1

    report_data = {
        "metadata": {
            "scope": scope,
            "template": template,
            "timestamp": timestamp,
            "methodology": "ISO 27001 Clause 6.1.2",
            "assessment_kind": "catalog_scenario_analysis",
            "demo": demo,
            "asset_source": "synthetic_demo" if demo else "user_supplied_csv",
            "asset_source_ref": asset_source,
            "control_source_ref": control_source,
            "scenario_source": f"bundled_catalog:{template}",
            "limitations": "Catalog scenario analysis, not a site scan or formal assessment. "
                           "Scope is a label, not system discovery. Threats, vulnerability candidates "
                           "and likelihoods are unverified catalog assumptions. Classification impact "
                           "comes from synthetic demo assets or the supplied inventory. "
                           "Unknown controls have no residual estimate; supplied evidence is not "
                           "independently verified. Treatment timelines are catalog suggestions.",
        },
        "summary": {
            "total_assets": len(assets),
            "total_risks": len(risks),
            "risk_distribution": risk_counts,
            "critical_risks": risk_counts["critical"],
            "high_risks": risk_counts["high"],
        },
        "assets": assets,
        "risks": risks,
        "residual_risks": [calculate_residual_risk(
            r, (controls or {}).get((r["asset_id"], r["threat_id"]))) for r in risks],
    }

    if output_format == "json":
        return json.dumps(report_data, indent=2)
    elif output_format == "csv":
        output = io.StringIO(newline="")
        rows = []
        for risk, residual in zip(risks, report_data["residual_risks"]):
            rows.append({**report_data["metadata"], **risk, **residual})
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
    else:  # markdown
        lines = [
            "# Catalog Scenario Analysis" + (" — DEMO (synthetic assets)" if demo else ""),
            f"",
            f"**Scope:** {scope}",
            f"**Template:** {template}",
            f"**Date:** {timestamp}",
            f"**Methodology:** ISO 27001 Clause 6.1.2",
            f"**Demo:** {demo}",
            f"**Asset source:** {report_data['metadata']['asset_source']} ({asset_source or 'built-in sample'})",
            f"**Scenario source:** bundled_catalog:{template}",
            f"**Control source:** {control_source or 'none'}",
            f"**Limitations:** {report_data['metadata']['limitations']}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Assets | {len(assets)} |",
            f"| Total Risks | {len(risks)} |",
            f"| Critical Risks | {risk_counts['critical']} |",
            f"| High Risks | {risk_counts['high']} |",
            f"| Medium Risks | {risk_counts['medium']} |",
            f"",
            f"## Asset Inventory",
            f"",
            f"| ID | Asset | Type | Owner | Classification |",
            f"|----|-------|------|-------|----------------|",
        ]
        for asset in assets:
            lines.append(
                f"| {asset['id']} | {asset['name']} | {asset['type']} | "
                f"{asset['owner']} | {asset['classification'].capitalize()} |"
            )

        lines.extend([
            f"",
            f"## Unverified Catalog Scenarios (scores are assumptions)",
            f"",
            f"| Risk ID | Asset | Threat | L | I | Score | Level |",
            f"|---------|-------|--------|---|---|-------|-------|",
        ])
        for risk in risks:
            lines.append(
                f"| {risk['id']} | {risk['asset_name']} | {risk['threat_name']} | "
                f"{risk['likelihood']} | {risk['impact']} | {risk['score']} | "
                f"{risk['level'].capitalize()} |"
            )

        lines.extend(["", "## Conditional Residual Estimates", ""])
        for residual in report_data["residual_risks"]:
            effect = residual["control_effectiveness"]
            effect_text = "unknown" if effect is None else f"{effect:.1%}"
            lines.append(
                f"- {residual['risk_id']}: control={residual['control_status']}; "
                f"effectiveness={effect_text}; residual={residual['residual_score']} "
                f"({residual['residual_status']}); evidence={residual['evidence_ref'] or 'none'}; "
                f"assessed_by={residual['assessed_by'] or 'unknown'}; "
                f"assessed_at={residual['assessed_at'] or 'unknown'}. {residual['basis']}"
            )

        lines.extend([
            f"",
            f"## Treatment Recommendations",
            f"",
        ])
        for level, treatment in TREATMENT_OPTIONS.items():
            count = risk_counts[level]
            if count > 0:
                lines.append(f"**{level.capitalize()} ({count} risks):** {treatment}")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Offline catalog scenario analysis - no discovery, scanning or evidence verification"
    )
    parser.add_argument(
        "--scope", "-s",
        required=True,
        help="Scope label only; does not discover or access the system"
    )
    parser.add_argument(
        "--template", "-t",
        choices=["general", "healthcare", "cloud"],
        default="general",
        help="Assessment template (default: general)"
    )
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--demo", action="store_true", help="Use labeled synthetic demo assets")
    inputs.add_argument(
        "--assets", "-a",
        help="Supplied asset CSV (id,name,classification required)"
    )
    parser.add_argument("--control-evidence", help="CSV of per-asset/threat control attestations")
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv", "markdown"],
        default="markdown",
        help="Output format (default: markdown)"
    )

    args = parser.parse_args()

    if args.demo and args.control_evidence:
        parser.error("--control-evidence requires --assets; demo assets are synthetic")
    try:
        assets = (generate_sample_assets(args.scope, args.template) if args.demo
                  else load_assets_from_csv(args.assets))
        controls = (load_control_evidence(args.control_evidence, assets, args.template)
                    if args.control_evidence else {})
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))

    # Perform risk assessment
    risks = assess_risks(assets, args.template)

    # Generate report
    report = generate_report(
        args.scope,
        args.template,
        assets,
        risks,
        args.format,
        demo=args.demo,
        asset_source=args.assets,
        control_source=args.control_evidence,
        controls=controls,
    )

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to: {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
