from typing import Annotated

from fastapi import Depends, HTTPException, status


async def get_current_user() -> dict[str, str]:
    # Placeholder until Supabase JWT validation is wired in Phase 1.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Auth not configured")


CurrentUser = Annotated[dict[str, str], Depends(get_current_user)]
