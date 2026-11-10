"""Pinned model choices. All Apache-2.0, so the service can ship in a closed commercial app.

Revisions are pinned: a model changing upstream would silently change every result.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    repo: str
    revision: str
    license: str

    @property
    def tag(self) -> str:
        return f"{self.repo.split('/')[-1]}@{self.revision[:7]}"


DETECTOR = ModelSpec("google/owlv2-base-patch16-ensemble", "cfd3195ba4ea9592eec887ded089f4c08eff231d", "apache-2.0")
CLASSIFIER = ModelSpec("google/siglip2-base-patch16-224", "75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2", "apache-2.0")
POSE = ModelSpec("usyd-community/vitpose-base-simple", "a93ac0c67e0b7e2c55287d21d4c460c8f3c54d45", "apache-2.0")
