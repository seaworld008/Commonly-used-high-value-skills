"""Exercise the imported AKS projection with sensitive Kubernetes evidence."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

FILTER = Path(__file__).resolve().parents[1] / (
    'skills/devops-sre/azure-kubernetes/azure-kubernetes-automatic-readiness/'
    'scripts/sanitize-readiness-input.jq'
)


@pytest.mark.skipif(shutil.which('jq') is None, reason='jq is not installed')
def test_projection_drops_secrets_and_preserves_readiness_evidence():
    secret = 'sensitive-fixture-value'
    pod = {
        'containers': [{
            'name': 'web', 'image': 'registry.invalid/app:latest',
            'env': [{'name': 'PASSWORD', 'value': secret}],
            'envFrom': [{'secretRef': {'name': secret}}],
            'resources': {'requests': {'cpu': '100m'}},
            'readinessProbe': {'httpGet': {'httpHeaders': [{'name': 'Auth', 'value': secret}]}},
            'securityContext': {
                'privileged': True,
                'seLinuxOptions': {'user': secret, 'role': secret, 'type': 'container_t'},
                'windowsOptions': {'runAsUserName': 'ContainerAdministrator'},
            },
        }],
        'volumes': [{'name': 'credentials', 'secret': {'secretName': secret}}],
    }
    source = {'apiVersion': 'v1', 'kind': 'List', 'items': [
        {'apiVersion': 'apps/v1', 'kind': 'Deployment',
         'metadata': {'name': 'web', 'annotations': {'private': secret}},
         'spec': {'replicas': 2, 'template': {'spec': pod}}, 'status': {'private': secret}},
        {'apiVersion': 'v1', 'kind': 'Secret', 'data': {'private': secret}},
        {'apiVersion': 'v1', 'kind': 'ConfigMap', 'data': {'private': secret}},
    ]}
    result = subprocess.run(['jq', '-f', str(FILTER)], input=json.dumps(source),
                            text=True, capture_output=True, check=True, timeout=10)
    assert secret not in result.stdout
    items = json.loads(result.stdout)['items']
    assert len(items) == 1
    spec = items[0]['spec']['template']['spec']
    container = spec['containers'][0]
    assert container['imagePolicy']['usesLatestTag'] is True
    assert container['readinessProbeConfigured'] is True
    assert container['livenessProbeConfigured'] is False
    assert container['resources']['requests']['cpu'] == '100m'
    assert container['securityContext']['seLinuxOptions']['userConfigured'] is True
    assert container['securityContext']['windowsOptions']['runsAsContainerAdministrator'] is True
    assert spec['volumes'][0]['types'] == ['secret']


@pytest.mark.skipif(shutil.which('jq') is None, reason='jq is not installed')
def test_projection_compares_service_selectors_without_releasing_them():
    source = {'kind': 'List', 'items': [
        {'kind': 'Service', 'metadata': {'name': 'one', 'namespace': 'ns'},
         'spec': {'selector': {'private-selector': 'do-not-emit'}}},
        {'kind': 'Service', 'metadata': {'name': 'two', 'namespace': 'ns'},
         'spec': {'selector': {'private-selector': 'do-not-emit'}}},
        {'kind': 'Service', 'metadata': {'name': 'other', 'namespace': 'different'},
         'spec': {'selector': {'private-selector': 'do-not-emit'}}},
    ]}
    result = subprocess.run(['jq', '-f', str(FILTER)], input=json.dumps(source),
                            text=True, capture_output=True, check=True, timeout=10)
    assert 'do-not-emit' not in result.stdout
    items = json.loads(result.stdout)['items']
    assert [item['selectorDuplicateCount'] for item in items] == [2, 2, 1]
