from pathlib import Path
from typing import Dict, Literal, Optional

AnalyzerProtocol = Literal["ASTM", "HL7"]

# Base directory for configs (relative to this file)
_BASE_DIR = Path(__file__).resolve().parent
_CONFIG_DIR = _BASE_DIR / "configs"

# Minimal registry; extend as needed
_ANALYZER_REGISTRY: Dict[str, Dict[str, str]] = {
	"BS240": {
		"protocol": "ASTM",
		"config": str(_CONFIG_DIR / "bs240.yaml"),
	},
	"Abbott": {
		"protocol": "ASTM",
		"config": str(_CONFIG_DIR / "abbott.yaml"),
	},
	"Snibe": {
		"protocol": "ASTM",
		"config": str(_CONFIG_DIR / "snibe.yaml"),
	},
	"ErbaElite580": {
		"protocol": "ASTM",
		"config": str(_CONFIG_DIR / "erba_elite_580.yaml"),
	},
}

def get_analyzer_info(name: str) -> Optional[Dict[str, str]]:
	"""Return registry entry for analyzer name, if present."""
	return _ANALYZER_REGISTRY.get(name) 