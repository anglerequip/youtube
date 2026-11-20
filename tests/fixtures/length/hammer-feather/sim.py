import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from beat_sim import BeatSim as Sim  # noqa: E402,F401
