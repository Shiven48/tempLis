"""
Profile Factory for creating machine-specific profiles
"""
from typing import Optional
from profiles.base_profile import BaseProfile
from profiles.bs240_profile import BS240Profile
from profiles.erba_elite_580_profile import ErbaElite580Profile

class ProfileFactory:
    """Factory class for creating machine profiles"""
    
    _profiles = {
        "BS_240": BS240Profile,
        "ERBA_ELITE_580": ErbaElite580Profile,
    }
    
    @classmethod
    def create_profile(cls, machine_type: str, config_path: Optional[str] = None) -> BaseProfile:
        """Create a profile instance for the specified machine type"""
        profile_class = cls._profiles.get(machine_type.upper())
        
        if not profile_class:
            raise ValueError(f"Unsupported machine type: {machine_type}")
        
        return profile_class(config_path)
    
    @classmethod
    def get_supported_machines(cls) -> list:
        """Get list of supported machine types"""
        return list(cls._profiles.keys())
    
    @classmethod
    def register_profile(cls, machine_type: str, profile_class: type):
        """Register a new profile class"""
        if not issubclass(profile_class, BaseProfile):
            raise ValueError("Profile class must inherit from BaseProfile")
        
        cls._profiles[machine_type.upper()] = profile_class