"""Test fixtures."""

from importlib import import_module
from pathlib import Path
from typing import Any

import boilerdaq
import pytest
from boilercore import filter_certain_warnings
from boilercore.paths import get_module_rel, walk_modules
from boilercore.testing import get_session_path
from boilerdaq.daq import Looper
from debugpy import is_client_connected
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from pyvisa import ResourceManager
from pyvisa.resources import MessageBasedResource

DEBUG = is_client_connected()

INSTRUMENT_NAME = "USB0::0x0957::0x0807::US25N3188G::0::INSTR"

STAGES_DIR = Path("src") / "boilerdaq" / "stages"
STAGES: list[Any] = []
for module in (f"boilerdaq.{module}" for module in walk_modules(STAGES_DIR)):
    rel_to_stages = get_module_rel(module, "stages")
    marks = [pytest.mark.skip] if rel_to_stages in {"controlled.set_voltage"} else []
    STAGES.append(
        pytest.param(module, id=get_module_rel(module, "stages"), marks=marks)
    )


@pytest.fixture(scope="session", autouse=True)
def _project_session_path(tmp_path_factory: pytest.TempPathFactory):
    """Set the project directory."""
    get_session_path(tmp_path_factory, boilerdaq)


@pytest.fixture(scope="session", autouse=True)
def _disable_power_supply():
    """Disable the power supply after testing."""
    try:
        yield
    finally:
        instrument: MessageBasedResource = ResourceManager().open_resource(  # type: ignore
            INSTRUMENT_NAME, read_termination="\n", write_termination="\n"
        )
        for instruction in ["output:state off", "source:current 0", "source:voltage 0"]:
            instrument.write(instruction)
        instrument.close()


# Can't be session scope
@pytest.fixture(autouse=True)
def _filter_certain_warnings():
    """Filter certain warnings."""
    filter_certain_warnings()


@pytest.fixture(params=STAGES)
def looper(request: pytest.FixtureRequest):
    """Test example procedures."""
    module = import_module(request.param)
    looper: Looper = getattr(module, "looper", lambda: None)() or module.main()
    app: QApplication = looper.app
    if not DEBUG:
        QTimer.singleShot(2000, app.closeAllWindows)
    return looper
