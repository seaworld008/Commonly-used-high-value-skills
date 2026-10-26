from copy import deepcopy
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/multimodal-media/remotion-video/scripts/validate_media.py'
spec = importlib.util.spec_from_file_location('remotion_acceptance', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample():
    return {'streams': [{'codec_type': 'video', 'width': 1280, 'height': 720,
                         'avg_frame_rate': '30/1', 'duration': '3.000000', 'nb_frames': '90'}]}


def validate(payload, **changes):
    contract = dict(width=1280, height=720, fps=Fraction(30), frames=90, audio='absent')
    contract.update(changes)
    return module.validate(payload, **contract)


def test_matching_metadata():
    assert validate(sample()) == []


@pytest.mark.parametrize('field,value,message', [('width', 1920, 'width'), ('height', 1080, 'height'),
    ('avg_frame_rate', '24/1', 'frame rate'), ('duration', '2.8', 'duration'), ('nb_frames', '89', 'frame count')])
def test_mismatch_is_not_accepted(field, value, message):
    payload = sample(); payload['streams'][0][field] = value
    assert any(message in failure for failure in validate(payload))


def test_exact_ntsc_rational_rate():
    payload = sample(); video = payload['streams'][0]
    video.update(avg_frame_rate='30000/1001', duration='3.003')
    assert validate(payload, fps=Fraction(30000, 1001)) == []


def test_duration_rounding_within_one_frame():
    payload = sample(); payload['streams'][0]['duration'] = '3.03'
    assert validate(payload) == []


def test_unknown_average_can_use_nominal_rate_and_container_duration():
    payload = sample(); video = payload['streams'][0]
    video.update(avg_frame_rate='0/0', r_frame_rate='30/1', duration='N/A')
    payload['format'] = {'duration': '3'}
    assert validate(payload) == []


def test_required_and_unexpected_audio():
    payload = sample()
    assert 'required audio stream is missing' in validate(payload, audio='present')
    payload['streams'].append({'codec_type': 'audio'})
    assert validate(payload, audio='present') == []
    assert 'unexpected audio stream' in validate(payload)


@pytest.mark.parametrize('value', ['nan', 'Infinity', '0', '-1', '1/0', '1e999999999', '1'*65, True, None])
def test_invalid_numbers_fail_cleanly(value):
    with pytest.raises(ValueError): module.positive_fraction(value, 'test')


def test_multiple_or_no_video_streams_rejected():
    payload = sample(); payload['streams'] *= 2
    assert validate(payload) == ['exactly one video stream is required']
    assert validate({'streams': []}) == ['exactly one video stream is required']


@pytest.mark.parametrize('raw', [b'{', b'\xff', b'[]', b'{"streams":[null]}', b'{"streams":[{"codec_type":"video","avg_frame_rate":[]}]}'])
def test_cli_invalid_input_has_bounded_diagnostic(tmp_path, raw):
    path = tmp_path / 'probe.json'; path.write_bytes(raw)
    result = subprocess.run([sys.executable, str(SCRIPT), str(path), '--width', '1280', '--height', '720', '--fps', '30', '--frames', '90'], capture_output=True, text=True)
    assert result.returncode == 1
    assert json.loads(result.stderr)['ok'] is False
    assert 'Traceback' not in result.stderr


def test_cli_acceptance_and_input_unchanged(tmp_path):
    path = tmp_path / 'probe.json'; raw = json.dumps(sample()).encode(); path.write_bytes(raw)
    result = subprocess.run([sys.executable, str(SCRIPT), str(path), '--width', '1280', '--height', '720', '--fps', '30', '--frames', '90', '--audio', 'absent'], capture_output=True, text=True)
    assert result.returncode == 0
    assert json.loads(result.stdout) == {'ok': True, 'failures': []}
    assert path.read_bytes() == raw


def test_cli_rejects_oversized_input(tmp_path):
    path = tmp_path / 'probe.json'; path.write_bytes(b' ' * (module.MAX_BYTES + 1))
    result = subprocess.run([sys.executable, str(SCRIPT), str(path), '--width', '1280', '--height', '720', '--fps', '30', '--frames', '90'], capture_output=True, text=True)
    assert result.returncode == 1 and 'Traceback' not in result.stderr
