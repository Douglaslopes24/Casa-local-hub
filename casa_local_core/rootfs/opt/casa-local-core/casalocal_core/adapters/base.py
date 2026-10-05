from abc import ABC, abstractmethod

from casalocal_core.models.device import DiscoveredDevice


class DiscoveryAdapter(ABC):
    name: str

    @abstractmethod
    async def discover(self, timeout: float) -> list[DiscoveredDevice]:
        raise NotImplementedError
