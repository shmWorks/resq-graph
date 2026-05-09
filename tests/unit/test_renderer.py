"""
test_renderer.py – Sprint 11 (US-041)
Unit tests for PygameRenderer under headless (SDL dummy) mode.
"""
import copy
import pytest
import pygame

from src.rendering.pygame_renderer import PygameRenderer
from src.simulation.simulation_engine import SimulationState
from src.simulation.ambulance import AmbulanceState

@pytest.fixture
def mock_node_positions():
    return {0: [100, 100], 1: [200, 200], 2: [300, 300], 3: [400, 400]}

@pytest.fixture
def headless_screen():
    # conftest.py already sets SDL_VIDEODRIVER=dummy
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    yield screen
    pygame.quit()

def test_renderer_initialises_headless(headless_screen, mock_node_positions):
    renderer = PygameRenderer(headless_screen, mock_node_positions, bg_image_path="invalid_path.png")
    assert renderer is not None
    assert renderer.screen == headless_screen
    # Should fallback to 1200x900 if bg image missing
    assert renderer.orig_size == (1200, 900)

def test_draw_does_not_mutate_sim_state(headless_screen, mock_node_positions):
    renderer = PygameRenderer(headless_screen, mock_node_positions)
    
    state = SimulationState(lambda_rate=0.1)
    state.current_tick = 42
    state.last_hdbscan_tick = 0
    state.paused = False
    
    class MockAmbulance:
        def __init__(self):
            self.id = "A1"
            self.pixel_pos = (100, 100)
            self.state = AmbulanceState.IDLE
            self.pixel_polyline = []

    ambulances = [MockAmbulance()]
    
    class MockDispatcher:
        def __init__(self):
            self.hotspot_hulls = []
            self.hotspot_centroids = []
            self.active_events = []
            
        @property
        def metrics_tracker(self):
            class MockTracker:
                events_resolved = 0
                def average_response_time(self): return 0.0
                recent_events = []
                def get_hud_data(self): return {}
            return MockTracker()
            
    dispatcher = MockDispatcher()
    
    state_copy = copy.deepcopy(state)
    # The actual draw method signature:
    # draw(state, ambulances, dispatcher, show_metrics_panel, show_hotspots, show_traffic, show_log, log_buffer, current_tick)
    renderer.draw(state, ambulances, dispatcher, False, False, False, False, [], 42)
    
    assert state.current_tick == state_copy.current_tick
    assert state.lambda_rate == state_copy.lambda_rate

def test_draw_path_no_error(headless_screen, mock_node_positions):
    renderer = PygameRenderer(headless_screen, mock_node_positions)
    # create dummy ambulance
    class MockAmbulance:
        def __init__(self):
            self.state = AmbulanceState.IN_TRANSIT
            self.pixel_polyline = [(10, 10), (20, 20)]
            
    renderer.draw_ambulance_paths([MockAmbulance()])

def test_hud_renders_with_empty_metrics(headless_screen, mock_node_positions):
    renderer = PygameRenderer(headless_screen, mock_node_positions)
    state = SimulationState(lambda_rate=0.1)
    state.current_tick = 0
    state.last_hdbscan_tick = 0
    state.paused = False
    
    hud_data = {
        "art": 0.0,
        "total_events": 0
    }
    renderer._draw_hud(state, [], 0, hud_data)

def test_sprite_loads_when_file_exists(headless_screen, tmp_path):
    # Instead of an actual _load_sprite test, we test the map background loads correctly
    # because the ambulance uses simple pygame.draw.circle calls.
    test_surface = pygame.Surface((32, 32))
    png_path = tmp_path / "test_bg.png"
    pygame.image.save(test_surface, str(png_path))
    
    # Instantiate PygameRenderer with valid bg
    renderer = PygameRenderer(headless_screen, {0: [100, 100]}, bg_image_path=str(png_path))
    assert renderer.orig_size == (32, 32)

def test_sprite_fallback_when_file_missing(headless_screen, mock_node_positions):
    # Fallback to 1200x900
    renderer = PygameRenderer(headless_screen, mock_node_positions, bg_image_path="invalid.png")
    assert renderer.orig_size == (1200, 900)
    
    # Also verify drawing ambulance works (no sprite to load, just circles)
    class DummyAmbulance:
        def __init__(self):
            self.id = 1
            self.pixel_pos = (10, 10)
            self.state = AmbulanceState.IDLE
    
    renderer._draw_ambulance(DummyAmbulance())
