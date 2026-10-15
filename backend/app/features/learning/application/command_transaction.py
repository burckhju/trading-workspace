"""Named public command boundaries; lower-level operations remain composable."""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Concatenate, Protocol

from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork


class CommandOwner(Protocol):
    _uow: LearningTradeLinkUnitOfWork


def committed_command[S: CommandOwner, **P, R](
    operation: Callable[Concatenate[S, P], Awaitable[R]],
) -> Callable[Concatenate[S, P], Awaitable[R]]:
    @wraps(operation)
    async def execute(owner: S, /, *args: P.args, **kwargs: P.kwargs) -> R:
        async with owner._uow:
            result = await operation(owner, *args, **kwargs)
            await owner._uow.commit()
            return result

    return execute
