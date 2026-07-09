"""Pipeline stage interface — every stage implements this."""

from abc import ABC, abstractmethod


class AbstractPipelineStage(ABC):
    """A single step in the analysis pipeline.
    Takes a context, does its work, returns the updated context."""

    @abstractmethod
    async def execute(self, context: "PipelineContext") -> "PipelineContext":  # type: ignore[name-defined]
        """Execute this stage. Never raises — errors go into context."""
        ...