from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Callable

class BaseCompiler(ABC):
    """
    Abstract base class for CodeVault compilers.
    Standardizes the build lifecycle across different languages.
    """
    def __init__(self, project_dir: Path, config: Dict[str, Any]):
        self.project_dir = project_dir
        self.config = config

    @abstractmethod
    async def pre_flight(self) -> bool:
        """
        Check for tools and environment readiness.
        Returns:
            bool: True if environment is ready for build.
        """
        pass

    @abstractmethod
    async def inject_wrapper(self) -> bool:
        """
        Inject license protection.
        Returns:
            bool: True if injection successful.
        """
        pass

    @abstractmethod
    async def compile(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, Optional[Path]]:
        """
        Execute the actual compilation/bundling.
        Args:
            progress_callback: Optional async-safe callback (percent, status_text)
        Returns:
            Tuple[bool, Optional[Path]]: (success: bool, build_dir: Path | None)
        """
        pass
