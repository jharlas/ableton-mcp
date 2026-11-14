"""Regression tests for Live's thread-affine bindings and snapshot fault isolation."""
import importlib.util
from pathlib import Path
import queue
import sys
import threading
import types
from types import SimpleNamespace as NS

import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def surface(monkeypatch):
    framework = types.ModuleType('_Framework.ControlSurface')
    framework.ControlSurface = object
    monkeypatch.setitem(sys.modules, '_Framework', types.ModuleType('_Framework'))
    monkeypatch.setitem(sys.modules, '_Framework.ControlSurface', framework)
    spec = importlib.util.spec_from_file_location('snapshot_remote_test', ROOT / 'AbletonMCP_Remote_Script/__init__.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    obj = mod.AbletonMCP.__new__(mod.AbletonMCP)
    obj.logs = []
    obj.log_message = obj.logs.append
    obj._song = song()
    obj.song = lambda: obj._song
    return obj

def mixer():
    return NS(volume=NS(value=.8), panning=NS(value=0), sends=[])

def device():
    return NS(name='Instrument', class_name='Instrument', class_display_name='Instrument', can_have_chains=False, can_have_drum_pads=False, parameters=[NS(name='Gain', value=.5, min=0, max=1, is_enabled=True, is_quantized=False)])

def clip():
    return NS(name='Clip', start_time=0., end_time=4., length=4., color=1, is_midi_clip=True, is_audio_clip=False, is_playing=False, looping=False, loop_start=0., loop_end=4., launch_mode=0, get_notes_extended=lambda *args: [NS(pitch=60,start_time=0.,duration=1.,velocity=100,mute=False)])

def track():
    return NS(name='Track', has_audio_input=False, has_midi_input=True, mute=False, solo=False, can_be_armed=True, arm=False, mixer_device=mixer(), devices=[device()], clip_slots=[NS(has_clip=True,clip=clip())], arrangement_clips=[clip()])

def song():
    return NS(tempo=100.,signature_numerator=4,signature_denominator=4,tracks=[track()],return_tracks=[],master_track=NS(mixer_device=mixer(),devices=[]),scenes=[],cue_points=[])

@pytest.mark.parametrize('action', ['get_session_info', 'get_session_snapshot'])
def test_dispatch_reads_fresh_song_on_main_thread(surface, action):
    main = threading.get_ident()
    current = song()
    class BoundSong:
        def __getattr__(self, key):
            assert threading.get_ident() == main, 'Live binding accessed on socket worker'
            return getattr(current, key)
    class StaleSong:
        def __getattr__(self, key):
            raise TypeError('None(TPyHandle<ASong>)')
    surface._song = StaleSong()
    surface.song = lambda: BoundSong()
    callbacks = queue.Queue()
    surface.schedule_message = lambda ticks, callback: callbacks.put(callback)
    result = []
    worker = threading.Thread(target=lambda: result.append(surface._process_command({'type':action,'params':{'include_notes':False,'include_params':False}})))
    worker.start()
    callbacks.get(timeout=2)()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert result[0]['status'] == 'success'
    payload = result[0]['result']
    assert (payload.get('session') or payload)['tempo'] == 100

@pytest.mark.parametrize('notes,params', [(False,False),(True,False),(False,True),(True,True)])
def test_optional_fields_and_schema(surface, notes, params):
    result = surface._get_session_snapshot(notes, params)
    assert set(result) == {'schema','session','tracks','scenes','return_tracks','master_track','cue_points','include_notes','include_params'}
    assert result['schema'] == 'ableton_mcp_snapshot_v2'
    t = result['tracks'][0]
    for c in (t['clip_slots'][0]['clip'], t['arrangement_clips'][0]):
        assert ('notes' in c) == notes
        if notes: assert c['notes'][0]['pitch'] == 60
    assert ('parameters' in t['devices'][0]) == params

class Broken:
    def __getattr__(self, name):
        raise RuntimeError('unsupported-property-test: ' + name)

def test_broken_track_does_not_abort_following_tracks(surface):
    surface._song.tracks.insert(0, Broken())
    result = surface._get_session_snapshot(False,False)
    assert result['tracks'][-1]['name'] == 'Track'
    assert any('Traceback' in line and 'unsupported-property-test' in line for line in surface.logs)

def test_broken_clips_devices_and_parameters_preserve_siblings(surface):
    t = surface._song.tracks[0]
    t.arrangement_clips.insert(0, Broken())
    t.devices.insert(0, Broken())
    t.devices[-1].parameters.insert(0, Broken())
    result = surface._get_session_snapshot(True,True)['tracks'][0]
    assert result['arrangement_clips'][-1]['notes'][0]['pitch'] == 60
    assert result['devices'][-1]['parameters'][0]['name'] == 'Gain'
    assert any('Traceback' in line for line in surface.logs)

def test_fatal_song_error_has_full_traceback_not_empty_success(surface):
    surface._song = Broken()
    with pytest.raises(RuntimeError): surface._get_session_snapshot(False,False)
    assert any('Snapshot failed' in line and 'Traceback' in line for line in surface.logs)

def test_scheduling_failure_never_runs_live_reader_on_worker(surface):
    surface.schedule_message = lambda *args: (_ for _ in ()).throw(AssertionError('scheduler unavailable'))
    called=[]
    with pytest.raises(AssertionError): surface._read_song_on_main_thread(lambda:called.append(1))
    assert called == []


def test_unavailable_master_mixer_does_not_abort_snapshot(surface):
    surface._song.master_track.mixer_device = Broken()
    result = surface._get_session_snapshot(False, False)
    assert result['session']['tempo'] == 100
    assert result['session']['master_track']['volume'] is None
    assert result['master_track']['panning'] is None
    assert result['tracks'][0]['name'] == 'Track'


@pytest.mark.parametrize('notes,params', [(False, False), (True, False), (False, True), (True, True)])
def test_mcp_handler_preserves_command_flags_and_payload(monkeypatch, notes, params):
    import json
    import MCP_Server.server as server
    import MCP_Server.script_handshake as handshake
    monkeypatch.setattr(handshake, 'require_capability', lambda name: None)
    sent = []
    expected = {'schema': 'ableton_mcp_snapshot_v2', 'tracks': []}
    def send(action, arguments):
        sent.append((action, arguments))
        return expected
    monkeypatch.setattr(server, 'get_ableton_connection', lambda: NS(send_command=send))
    assert json.loads(server.get_session_snapshot(None, notes, params)) == expected
    assert sent == [('get_session_snapshot', {'include_notes': notes, 'include_params': params})]


def test_mcp_handler_logs_full_traceback(monkeypatch, caplog):
    import MCP_Server.server as server
    import MCP_Server.script_handshake as handshake
    monkeypatch.setattr(handshake, 'require_capability', lambda name: None)
    def send(*args):
        raise RuntimeError('binding-failure-test')
    monkeypatch.setattr(server, 'get_ableton_connection', lambda: NS(send_command=send))
    assert server.get_session_snapshot(None, False, False) == 'Error getting session snapshot: binding-failure-test'
    assert 'Traceback' in caplog.text and 'include_notes=False, include_params=False' in caplog.text


def test_installer_bundle_matches_remote_script():
    import MCP_Server.remote_script_install as install
    source = ROOT / 'AbletonMCP_Remote_Script/__init__.py'
    bundle = ROOT / 'MCP_Server/bundled_ableton_remote_script/AbletonMCP_init.py'
    assert source.read_bytes() == bundle.read_bytes()
    assert ('SCRIPT_VERSION = "' + install.EXPECTED_REMOTE_SCRIPT_VERSION + '"') in source.read_text()
