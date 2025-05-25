import os
import json
from typing import Dict, List, Optional

PROFILES_FILE = "svn_profiles.json"

class Profile:
    def __init__(self, name: str, svn_path: str, patch_prefix: List[str], current_patches: str, dsn_name: str):
        self.name = name
        self.svn_path = svn_path
        self.patch_prefix = patch_prefix
        self.current_patches = current_patches
        self.dsn_name = dsn_name

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "svn_path": self.svn_path,
            "patch_prefix": self.patch_prefix,
            "current_patches": self.current_patches,
            "dsn_name": self.dsn_name
        }

    @staticmethod
    def from_dict(data: dict) -> 'Profile':
        return Profile(
            name=data["name"],
            svn_path=data["svn_path"],
            patch_prefix=data["patch_prefix"],
            current_patches=data["current_patches"],
            dsn_name=data["dsn_name"]
        )

def load_profiles() -> Dict[str, Profile]:
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, "r") as f:
            data = json.load(f)
            return {name: Profile.from_dict(profile_data) 
                   for name, profile_data in data.items()}
    return {}

def save_profiles(profiles: Dict[str, Profile]) -> None:
    with open(PROFILES_FILE, "w") as f:
        json.dump({name: profile.to_dict() 
                  for name, profile in profiles.items()}, f, indent=2)

def create_profile(name: str, svn_path: str, patch_prefix: List[str], 
                  current_patches: str, dsn_name: str) -> Profile:
    profiles = load_profiles()
    if name in profiles:
        raise ValueError(f"Profile '{name}' already exists")
    
    profile = Profile(name, svn_path, patch_prefix, current_patches, dsn_name)
    profiles[name] = profile
    save_profiles(profiles)
    return profile

def update_profile(name: str, svn_path: Optional[str] = None, 
                  patch_prefix: Optional[List[str]] = None,
                  current_patches: Optional[str] = None,
                  dsn_name: Optional[str] = None) -> Profile:
    """Update an existing profile with new values."""
    profiles = load_profiles()
    if name not in profiles:
        raise ValueError(f"Profile '{name}' does not exist")
    
    profile = profiles[name]
    
    # Update only provided values
    if svn_path is not None:
        profile.svn_path = svn_path
    if patch_prefix is not None:
        profile.patch_prefix = patch_prefix
    if current_patches is not None:
        profile.current_patches = current_patches
    if dsn_name is not None:
        profile.dsn_name = dsn_name
    
    save_profiles(profiles)
    return profile

def delete_profile(name: str) -> None:
    profiles = load_profiles()
    if name not in profiles:
        raise ValueError(f"Profile '{name}' does not exist")
    
    del profiles[name]
    save_profiles(profiles)

def get_profile(name: str) -> Optional[Profile]:
    profiles = load_profiles()
    return profiles.get(name)

def list_profiles() -> List[str]:
    return list(load_profiles().keys()) 