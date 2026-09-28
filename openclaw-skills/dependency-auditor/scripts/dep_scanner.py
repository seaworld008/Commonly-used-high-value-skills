#!/usr/bin/env python3
"""
Dependency Scanner - Best-effort, offline dependency inventory.

This script inventories selected manifests and lockfiles without network access.
It does not assess vulnerabilities. Use maintained ecosystem scanners for security
gates; legacy --fail-on-high exits 2 when no assessment is available.

Author: Claude Skills Engineering Team
License: MIT
"""

import json
import os
import re
import sys
import argparse
from typing import Dict, List, Set, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import subprocess

@dataclass
class Vulnerability:
    """Represents a security vulnerability."""
    id: str
    summary: str
    severity: str
    cvss_score: float
    affected_versions: str
    fixed_version: Optional[str]
    published_date: str
    references: List[str]

@dataclass
class Dependency:
    """Represents a project dependency."""
    name: str
    version: str
    ecosystem: str
    direct: bool
    license: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None
    vulnerabilities: List[Vulnerability] = None
    
    def __post_init__(self):
        if self.vulnerabilities is None:
            self.vulnerabilities = []

class DependencyScanner:
    """Main dependency scanner class."""
    
    def __init__(self):
        self.supported_files = {
            'package.json': self._parse_package_json,
            'package-lock.json': self._parse_package_lock,
            'yarn.lock': self._parse_yarn_lock,
            'requirements.txt': self._parse_requirements_txt,
            'pyproject.toml': self._parse_pyproject_toml,
            'Pipfile.lock': self._parse_pipfile_lock,
            'poetry.lock': self._parse_poetry_lock,
            'go.mod': self._parse_go_mod,
            'Cargo.toml': self._parse_cargo_toml,
            'Cargo.lock': self._parse_cargo_lock,
            'Gemfile': self._parse_gemfile,
            'Gemfile.lock': self._parse_gemfile_lock,
        }
    
    def scan_project(self, project_path: str, *, quick_scan: bool = False) -> Dict[str, Any]:
        """Inventory dependencies; never interpret absent advisory data as safe."""
        project_path = Path(project_path)
        
        if not project_path.is_dir():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")
        
        scan_results = {
            'timestamp': datetime.now().isoformat(),
            'project_path': str(project_path),
            'dependencies': [],
            'vulnerabilities_found': 0,
            'high_severity_count': 0,
            'medium_severity_count': 0,
            'low_severity_count': 0,
            'ecosystems': set(),
            'scan_summary': {},
            'recommendations': [],
            'inventory_status': 'best_effort',
            'vulnerability_status': 'not_assessed',
            'advisory_source': None,
            'parse_errors': [],
            'inventory_notes': [
                'go.sum is checksum evidence, not a resolved dependency lockfile; it is not parsed.',
                'Manifest version ranges and simplified parsers are not an authoritative build graph.',
            ],
        }
        
        # Find and parse dependency files
        for file_pattern, parser in self.supported_files.items():
            matching_files = list(project_path.rglob(file_pattern))
            
            for dep_file in matching_files:
                try:
                    dependencies = parser(dep_file)
                    if quick_scan:
                        dependencies = [dep for dep in dependencies if dep.direct]
                    scan_results['dependencies'].extend(dependencies)
                    
                    for dep in dependencies:
                        scan_results['ecosystems'].add(dep.ecosystem)
                        
                except Exception as e:
                    scan_results['parse_errors'].append({'path': str(dep_file), 'error': str(e)})
                    scan_results['inventory_status'] = 'partial'

        scan_results['ecosystems'] = list(scan_results['ecosystems'])
        scan_results['scan_summary'] = self._generate_scan_summary(scan_results)
        scan_results['recommendations'] = self._generate_recommendations(scan_results)
        
        return scan_results
    
    # Package file parsers
    
    def _parse_package_json(self, file_path: Path) -> List[Dependency]:
        """Parse package.json for Node.js dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Parse dependencies
            for dep_type in ['dependencies', 'devDependencies']:
                if dep_type in data:
                    for name, version in data[dep_type].items():
                        dep = Dependency(
                            name=name,
                            version=version.replace('^', '').replace('~', '').replace('>=', '').replace('<=', ''),
                            ecosystem='npm',
                            direct=True
                        )
                        dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing package.json: {e}") from e
        
        return dependencies
    
    def _parse_package_lock(self, file_path: Path) -> List[Dependency]:
        """Parse package-lock.json for Node.js transitive dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if 'packages' in data:
                for path, pkg_info in data['packages'].items():
                    if path == '':  # Skip root package
                        continue
                    
                    name = path.split('/')[-1] if '/' in path else path
                    version = pkg_info.get('version', '')
                    
                    dep = Dependency(
                        name=name,
                        version=version,
                        ecosystem='npm',
                        direct=False,
                        description=pkg_info.get('description', '')
                    )
                    dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing package-lock.json: {e}") from e
        
        return dependencies
    
    def _parse_yarn_lock(self, file_path: Path) -> List[Dependency]:
        """Parse yarn.lock for Node.js dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            # Yarn v1 records are header lines followed by indented metadata.
            # Parse them as a small state machine so hostile lockfiles cannot
            # trigger catastrophic regular-expression backtracking.
            package_spec = None
            for raw_line in lines:
                stripped = raw_line.strip()
                if (
                    stripped
                    and not raw_line[:1].isspace()
                    and not stripped.startswith('#')
                    and stripped.endswith(':')
                ):
                    package_spec = stripped[:-1]
                    continue

                version_prefix = 'version "'
                if (
                    package_spec is not None
                    and stripped.startswith(version_prefix)
                    and stripped.endswith('"')
                ):
                    version = stripped[len(version_prefix):-1]
                    first_selector = package_spec.split(',', 1)[0].strip().strip('"')
                    if first_selector.startswith('@'):
                        slash_index = first_selector.find('/')
                        range_index = first_selector.find('@', slash_index + 1)
                    else:
                        range_index = first_selector.find('@')
                    name = (
                        first_selector[:range_index]
                        if range_index > 0
                        else first_selector
                    )
                    dependencies.append(Dependency(
                        name=name,
                        version=version,
                        ecosystem='npm',
                        direct=False
                    ))
                    package_spec = None
        
        except Exception as e:
            raise ValueError(f"Error parsing yarn.lock: {e}") from e
        
        return dependencies
    
    def _parse_requirements_txt(self, file_path: Path) -> List[Dependency]:
        """Parse requirements.txt for Python dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Parse package==version or package>=version patterns
                    match = re.match(r'^([a-zA-Z0-9_-]+)([><=!]+)(.+)$', line)
                    if match:
                        name, operator, version = match.groups()
                        dep = Dependency(
                            name=name,
                            version=version,
                            ecosystem='pypi',
                            direct=True
                        )
                        dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing requirements.txt: {e}") from e
        
        return dependencies
    
    def _parse_pyproject_toml(self, file_path: Path) -> List[Dependency]:
        """Parse pyproject.toml for Python dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Simple TOML parsing for dependencies
            dep_section = re.search(r'\[tool\.poetry\.dependencies\](.*?)(?=\[|\Z)', content, re.DOTALL)
            if dep_section:
                for line in dep_section.group(1).split('\n'):
                    match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']', line.strip())
                    if match:
                        name, version = match.groups()
                        if name != 'python':
                            dep = Dependency(
                                name=name,
                                version=version.replace('^', '').replace('~', ''),
                                ecosystem='pypi',
                                direct=True
                            )
                            dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing pyproject.toml: {e}") from e
        
        return dependencies
    
    def _parse_pipfile_lock(self, file_path: Path) -> List[Dependency]:
        """Parse Pipfile.lock for Python dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            for section in ['default', 'develop']:
                if section in data:
                    for name, info in data[section].items():
                        version = info.get('version', '').replace('==', '')
                        dep = Dependency(
                            name=name,
                            version=version,
                            ecosystem='pypi',
                            direct=(section == 'default')
                        )
                        dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing Pipfile.lock: {e}") from e
        
        return dependencies
    
    def _parse_poetry_lock(self, file_path: Path) -> List[Dependency]:
        """Parse poetry.lock for Python dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract package entries from TOML
            packages = re.findall(r'\[\[package\]\]\nname\s*=\s*"([^"]+)"\nversion\s*=\s*"([^"]+)"', content)
            
            for name, version in packages:
                dep = Dependency(
                    name=name,
                    version=version,
                    ecosystem='pypi',
                    direct=False
                )
                dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing poetry.lock: {e}") from e
        
        return dependencies
    
    def _parse_go_mod(self, file_path: Path) -> List[Dependency]:
        """Parse go.mod for Go dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse require block
            require_match = re.search(r'require\s*\((.*?)\)', content, re.DOTALL)
            if require_match:
                requires = require_match.group(1)
                for line in requires.split('\n'):
                    match = re.match(r'\s*([^\s]+)\s+v?([^\s]+)', line.strip())
                    if match:
                        name, version = match.groups()
                        dep = Dependency(
                            name=name,
                            version=version,
                            ecosystem='go',
                            direct=True
                        )
                        dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing go.mod: {e}") from e
        
        return dependencies
    
    def _parse_cargo_toml(self, file_path: Path) -> List[Dependency]:
        """Parse Cargo.toml for Rust dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse [dependencies] section
            dep_section = re.search(r'\[dependencies\](.*?)(?=\[|\Z)', content, re.DOTALL)
            if dep_section:
                for line in dep_section.group(1).split('\n'):
                    match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*["\']([^"\']+)["\']', line.strip())
                    if match:
                        name, version = match.groups()
                        dep = Dependency(
                            name=name,
                            version=version,
                            ecosystem='cargo',
                            direct=True
                        )
                        dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing Cargo.toml: {e}") from e
        
        return dependencies
    
    def _parse_cargo_lock(self, file_path: Path) -> List[Dependency]:
        """Parse Cargo.lock for Rust dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse [[package]] entries
            packages = re.findall(r'\[\[package\]\]\nname\s*=\s*"([^"]+)"\nversion\s*=\s*"([^"]+)"', content)
            
            for name, version in packages:
                dep = Dependency(
                    name=name,
                    version=version,
                    ecosystem='cargo',
                    direct=False
                )
                dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing Cargo.lock: {e}") from e
        
        return dependencies
    
    def _parse_gemfile(self, file_path: Path) -> List[Dependency]:
        """Parse Gemfile for Ruby dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse gem declarations
            gems = re.findall(r'gem\s+["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']+)["\'])?', content)
            
            for gem_info in gems:
                name = gem_info[0]
                version = gem_info[1] if len(gem_info) > 1 and gem_info[1] else ''
                
                dep = Dependency(
                    name=name,
                    version=version,
                    ecosystem='rubygems',
                    direct=True
                )
                dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing Gemfile: {e}") from e
        
        return dependencies
    
    def _parse_gemfile_lock(self, file_path: Path) -> List[Dependency]:
        """Parse Gemfile.lock for Ruby dependencies."""
        dependencies = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract GEM section
            gem_section = re.search(r'GEM\s*\n(.*?)(?=\n\S|\Z)', content, re.DOTALL)
            if gem_section:
                specs = gem_section.group(1)
                gems = re.findall(r'\s+([a-zA-Z0-9_-]+)\s+\(([^)]+)\)', specs)
                
                for name, version in gems:
                    dep = Dependency(
                        name=name,
                        version=version,
                        ecosystem='rubygems',
                        direct=False
                    )
                    dependencies.append(dep)
        
        except Exception as e:
            raise ValueError(f"Error parsing Gemfile.lock: {e}") from e
        
        return dependencies
    
    def _generate_scan_summary(self, scan_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the scan results."""
        total_deps = len(scan_results['dependencies'])
        unique_deps = len(set(dep.name for dep in scan_results['dependencies']))
        
        return {
            'total_dependencies': total_deps,
            'unique_dependencies': unique_deps,
            'ecosystems_found': len(scan_results['ecosystems']),
            'vulnerable_dependencies': len([dep for dep in scan_results['dependencies'] if dep.vulnerabilities]),
            'vulnerability_breakdown': {
                'high': scan_results['high_severity_count'],
                'medium': scan_results['medium_severity_count'],
                'low': scan_results['low_severity_count']
            }
        }
    
    def _generate_recommendations(self, scan_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on scan results."""
        recommendations = ["Run a maintained ecosystem advisory scanner: vulnerabilities are NOT ASSESSED by this offline inventory."]
        
        high_count = scan_results['high_severity_count']
        medium_count = scan_results['medium_severity_count']
        
        if high_count > 0:
            recommendations.append(f"URGENT: Address {high_count} high-severity vulnerabilities immediately")
        
        if medium_count > 0:
            recommendations.append(f"Schedule fixes for {medium_count} medium-severity vulnerabilities within 30 days")
        
        vulnerable_deps = [dep for dep in scan_results['dependencies'] if dep.vulnerabilities]
        if vulnerable_deps:
            for dep in vulnerable_deps[:3]:  # Top 3 most critical
                for vuln in dep.vulnerabilities:
                    if vuln.fixed_version:
                        recommendations.append(f"Update {dep.name} from {dep.version} to {vuln.fixed_version} to fix {vuln.id}")
        
        if len(scan_results['ecosystems']) > 3:
            recommendations.append("Consider consolidating package managers to reduce complexity")
        
        return recommendations
    
    def generate_report(self, scan_results: Dict[str, Any], format: str = 'text') -> str:
        """Generate a human-readable or JSON report."""
        if format == 'json':
            # Convert Dependency objects to dicts for JSON serialization
            serializable_results = scan_results.copy()
            serializable_results['dependencies'] = [
                {
                    'name': dep.name,
                    'version': dep.version,
                    'ecosystem': dep.ecosystem,
                    'direct': dep.direct,
                    'license': dep.license,
                    'vulnerabilities': [asdict(vuln) for vuln in dep.vulnerabilities]
                }
                for dep in scan_results['dependencies']
            ]
            return json.dumps(serializable_results, indent=2, default=str)
        
        # Text format report
        report = []
        report.append("=" * 60)
        report.append("DEPENDENCY INVENTORY REPORT")
        report.append("Vulnerability assessment: NOT ASSESSED (no advisory database)")
        report.append("=" * 60)
        report.append(f"Scan Date: {scan_results['timestamp']}")
        report.append(f"Project: {scan_results['project_path']}")
        report.append("")
        
        # Summary
        summary = scan_results['scan_summary']
        report.append("SUMMARY:")
        report.append(f"  Total Dependencies: {summary['total_dependencies']}")
        report.append(f"  Unique Dependencies: {summary['unique_dependencies']}")
        report.append(f"  Ecosystems: {', '.join(scan_results['ecosystems'])}")
        report.append(f"  Vulnerabilities Found: {scan_results['vulnerabilities_found']}")
        report.append(f"    High Severity: {summary['vulnerability_breakdown']['high']}")
        report.append(f"    Medium Severity: {summary['vulnerability_breakdown']['medium']}")
        report.append(f"    Low Severity: {summary['vulnerability_breakdown']['low']}")
        report.append("")
        
        # Vulnerable dependencies
        vulnerable_deps = [dep for dep in scan_results['dependencies'] if dep.vulnerabilities]
        if vulnerable_deps:
            report.append("VULNERABLE DEPENDENCIES:")
            report.append("-" * 30)
            
            for dep in vulnerable_deps:
                report.append(f"Package: {dep.name} v{dep.version} ({dep.ecosystem})")
                for vuln in dep.vulnerabilities:
                    report.append(f"  • {vuln.id}: {vuln.summary}")
                    report.append(f"    Severity: {vuln.severity} (CVSS: {vuln.cvss_score})")
                    if vuln.fixed_version:
                        report.append(f"    Fixed in: {vuln.fixed_version}")
                    report.append("")
        
        # Recommendations
        if scan_results['recommendations']:
            report.append("RECOMMENDATIONS:")
            report.append("-" * 20)
            for i, rec in enumerate(scan_results['recommendations'], 1):
                report.append(f"{i}. {rec}")
            report.append("")
        
        report.append("=" * 60)
        return '\n'.join(report)

def main():
    """Main entry point for the dependency scanner."""
    parser = argparse.ArgumentParser(
        description='Inventory project dependencies offline; this is not a vulnerability scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dep_scanner.py /path/to/project
  python dep_scanner.py . --format json --output results.json
  python dep_scanner.py /app --fail-on-high
        """
    )
    
    parser.add_argument('project_path', 
                       help='Path to the project directory to scan')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--output', '-o',
                       help='Output file path (default: stdout)')
    parser.add_argument('--fail-on-high', action='store_true',
                       help='Legacy security gate: exits 2 because vulnerabilities are not assessed')
    parser.add_argument('--quick-scan', action='store_true',
                       help='Perform quick scan (skip transitive dependencies)')
    
    args = parser.parse_args()
    
    try:
        scanner = DependencyScanner()
        results = scanner.scan_project(args.project_path, quick_scan=args.quick_scan)
        report = scanner.generate_report(results, args.format)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"Report saved to {args.output}")
        else:
            print(report)
        
        # Fail closed: missing advisory coverage must never pass a security gate.
        if args.fail_on_high:
            print('Security gate unavailable: run a maintained vulnerability scanner.', file=sys.stderr)
            sys.exit(2)
        if results['parse_errors']:
            sys.exit(2)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
