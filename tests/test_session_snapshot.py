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
    class ControlSurface:
        def update_display(self):
            self.parent_ticks += 1
    framework.ControlSurface = ControlSurface
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
    obj.parent_ticks = 0
    obj._initialize_song_reads()
    obj.submitted = queue.Queue()
    put = obj._song_reads.put_nowait
    def observe_put(request):
        put(request)
        obj.submitted.put(request)
    obj._song_reads.put_nowait = observe_put
    def forbidden_schedule(*args):
        raise AssertionError('Song reads must not use Live task scheduling')
    obj.schedule_message = forbidden_schedule
    return obj

def start_read(surface, reader):
    result = []
    finished = threading.Event()
    def run():
        try:
            result.append(surface._read_song_on_main_thread(reader))
        except Exception as exc:
            result.append(exc)
        finally:
            finished.set()
    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    return worker, result, finished

def finish_read(read):
    worker, result, finished = read
    assert finished.wait(2), 'socket worker did not receive its result'
    worker.join(timeout=2)
    assert not worker.is_alive()
    return result[0]

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
    result = []
    worker = threading.Thread(target=lambda: result.append(surface._process_command({'type':action,'params':{'include_notes':False,'include_params':False}})))
    worker.start()
    surface.submitted.get(timeout=2)
    assert result == []
    surface.update_display()
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

def test_expired_waiter_never_runs_reader_on_a_later_tick(surface):
    surface._SONG_READ_TIMEOUT = .05
    called = []
    read = start_read(surface, lambda: called.append(1))
    surface.submitted.get(timeout=2)
    error = finish_read(read)
    assert isinstance(error, RuntimeError)
    assert 'phase=queue' in str(error)
    surface.update_display()
    assert called == []
    assert surface._song_reads.unfinished_tasks == 0


def test_deadline_is_checked_before_live_access(surface):
    called = []
    read = start_read(surface, lambda: called.append(1))
    request = surface.submitted.get(timeout=2)
    with request['lock']:
        request['deadline'] = 0
    surface.update_display()
    assert 'phase=queue' in str(finish_read(read))
    assert called == []


def test_concurrent_reads_are_bounded_and_run_on_main_thread(surface):
    main = threading.get_ident()
    reads = [start_read(surface, lambda n=n: (n, threading.get_ident())) for n in range(8)]
    for _ in reads:
        surface.submitted.get(timeout=2)
    surface.update_display()
    assert surface._song_reads.qsize() == 6
    for _ in range(3):
        surface.update_display()
    assert [finish_read(read) for read in reads] == [(n, main) for n in range(8)]
    assert surface.parent_ticks == 4
    assert surface._song_reads.unfinished_tasks == 0


def test_enqueue_during_drain_is_not_lost(surface):
    surface._SONG_READS_PER_TICK = 1
    subsequent = []
    def first_reader():
        subsequent.append(start_read(surface, lambda: 'second'))
        surface.submitted.get(timeout=2)
        return 'first'
    first = start_read(surface, first_reader)
    surface.submitted.get(timeout=2)
    surface.update_display()
    assert finish_read(first) == 'first'
    assert not subsequent[0][2].is_set()
    surface.update_display()
    assert finish_read(subsequent[0]) == 'second'


def test_running_read_timeout_discards_late_result(surface):
    # Shorten the deadline only after execution starts, avoiding scheduler races.
    def reader():
        with request['lock']:
            request['deadline'] = 0
        return 'too late'
    read = start_read(surface, reader)
    request = surface.submitted.get(timeout=2)
    surface.update_display()
    error = finish_read(read)
    assert isinstance(error, RuntimeError)
    assert 'phase=execution' in str(error)
    assert request['state'] == 'expired'


def test_waiter_can_expire_while_live_reader_is_running(surface):
    surface._SONG_READ_TIMEOUT = .2
    entered = []
    def reader():
        entered.append(True)
        assert read[2].wait(2)
        return 'late result must not replace the timeout'
    read = start_read(surface, reader)
    request = surface.submitted.get(timeout=2)
    surface.update_display()
    assert entered == [True]
    error = finish_read(read)
    assert isinstance(error, RuntimeError)
    assert 'phase=execution' in str(error)
    assert request['result'] == (False, error)
    assert request['state'] == 'expired'


def test_disconnect_releases_waiters_and_rejects_new_reads(surface):
    called = []
    read = start_read(surface, lambda: called.append(1))
    surface.submitted.get(timeout=2)
    surface._close_song_reads()
    assert 'disconnected before Song read' in str(finish_read(read))
    surface.update_display()
    assert called == []
    with pytest.raises(RuntimeError, match='dispatcher is disconnected'):
        surface._read_song_on_main_thread(lambda: None)


def test_reader_failure_reaches_caller_and_next_read_succeeds(surface):
    def broken():
        raise ValueError('Live read failed')
    first = start_read(surface, broken)
    surface.submitted.get(timeout=2)
    second = start_read(surface, lambda: 'healthy')
    surface.submitted.get(timeout=2)
    surface.update_display()
    assert isinstance(finish_read(first), ValueError)
    assert finish_read(second) == 'healthy'
    assert any('Song read failed request_id=1' in line for line in surface.logs)
    assert any('queue_wait=' in line for line in surface.logs)
    assert any('execution=' in line for line in surface.logs)


def test_main_thread_read_executes_directly_with_fresh_song(surface):
    fresh = song()
    fresh.tempo = 120
    surface.song = lambda: fresh
    assert surface._read_song_on_main_thread(lambda: surface._song.tempo) == 120
    assert surface._song_reads.empty()


def test_full_queue_rejects_extra_request_without_blocking(surface):
    surface._song_reads.maxsize = 1
    first = start_read(surface, lambda: 'first')
    surface.submitted.get(timeout=2)
    extra = start_read(surface, lambda: 'extra')
    assert 'queue is full' in str(finish_read(extra))
    surface.update_display()
    assert finish_read(first) == 'first'


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
