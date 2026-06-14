from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app.models import User, Follow
from app.schemas import FollowResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/follows", tags=["Follows"])

@router.post("/{user_id}/follow", response_model=FollowResponse)
async def follow_user(
    user_id: int,  # The user to follow
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Follow a user"""
    
    # Can't follow yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_follow = result.scalar_one_or_none()
    
    if not user_to_follow:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already following
    result = await db.execute(
        select(Follow).where(
            and_(
                Follow.follower_id == current_user.id,
                Follow.following_id == user_id
            )
        )
    )
    existing_follow = result.scalar_one_or_none()
    
    if existing_follow:
        raise HTTPException(status_code=400, detail="Already following this user")
    
    # Create follow relationship
    new_follow = Follow(
        follower_id=current_user.id,
        following_id=user_id
    )
    
    db.add(new_follow)
    await db.commit()
    await db.refresh(new_follow)
    
    return new_follow

@router.delete("/{user_id}/unfollow")
async def unfollow_user(
    user_id: int,  # The user to unfollow
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unfollow a user"""
    
    # Find the follow relationship
    result = await db.execute(
        select(Follow).where(
            and_(
                Follow.follower_id == current_user.id,
                Follow.following_id == user_id
            )
        )
    )
    follow = result.scalar_one_or_none()
    
    if not follow:
        raise HTTPException(status_code=400, detail="Not following this user")
    
    await db.delete(follow)
    await db.commit()
    
    return {"message": f"Unfollowed user {user_id} successfully"}

@router.get("/followers")
async def get_my_followers(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of users who follow me"""
    
    result = await db.execute(
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.following_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    followers = result.scalars().all()
    
    return {
        "count": len(followers),
        "followers": followers
    }

@router.get("/following")
async def get_my_following(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of users I follow"""
    
    result = await db.execute(
        select(User)
        .join(Follow, Follow.following_id == User.id)
        .where(Follow.follower_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    following = result.scalars().all()
    
    return {
        "count": len(following),
        "following": following
    }

@router.get("/{user_id}/followers")
async def get_user_followers(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get followers of any user (respects privacy)"""
    
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check privacy
    if not user.is_public and user_id != current_user.id:
        # Check if current user follows this private account
        follow_check = await db.execute(
            select(Follow).where(
                and_(
                    Follow.follower_id == current_user.id,
                    Follow.following_id == user_id
                )
            )
        )
        if not follow_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Private account - cannot view followers")
    
    result = await db.execute(
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.following_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    followers = result.scalars().all()
    
    return {
        "user_id": user_id,
        "username": user.username,
        "followers_count": len(followers) if limit == 20 else "use skip/limit",
        "followers": followers
    }

@router.get("/{user_id}/following")
async def get_user_following(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get following list of any user (respects privacy)"""
    
    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check privacy
    if not user.is_public and user_id != current_user.id:
        follow_check = await db.execute(
            select(Follow).where(
                and_(
                    Follow.follower_id == current_user.id,
                    Follow.following_id == user_id
                )
            )
        )
        if not follow_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Private account - cannot view following")
    
    result = await db.execute(
        select(User)
        .join(Follow, Follow.following_id == User.id)
        .where(Follow.follower_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    following = result.scalars().all()
    
    return {
        "user_id": user_id,
        "username": user.username,
        "following_count": len(following) if limit == 20 else "use skip/limit",
        "following": following
    }