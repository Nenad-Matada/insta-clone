from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models import User, Follow, Post, Story
from app.schemas import UserResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
async def get_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's own data (full access)"""
    
    # Get additional stats for current user
    posts_count_result = await db.execute(
        select(func.count()).select_from(Post).where(Post.user_id == current_user.id)
    )
    posts_count = posts_count_result.scalar()
    
    followers_count_result = await db.execute(
        select(func.count()).select_from(Follow).where(Follow.following_id == current_user.id)
    )
    followers_count = followers_count_result.scalar()
    
    following_count_result = await db.execute(
        select(func.count()).select_from(Follow).where(Follow.follower_id == current_user.id)
    )
    following_count = following_count_result.scalar()
    
    stories_count_result = await db.execute(
        select(func.count()).select_from(Story)
        .where(Story.user_id == current_user.id)
        .where(Story.expires_at > datetime.utcnow())
    )
    active_stories_count = stories_count_result.scalar()
    
    return {
        **current_user.__dict__,
        "posts_count": posts_count,
        "followers_count": followers_count,
        "following_count": following_count,
        "active_stories_count": active_stories_count
    }

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """View another user's profile (respects privacy settings)"""
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check privacy
    is_private_account = not user.is_public
    is_owner = (user_id == current_user.id)
    is_following = False
    
    if not is_owner and is_private_account:
        # Check if current user follows this private account
        follow_result = await db.execute(
            select(Follow).where(
                and_(
                    Follow.follower_id == current_user.id,
                    Follow.following_id == user_id
                )
            )
        )
        is_following = follow_result.scalar_one_or_none() is not None
        
        if not is_following:
            raise HTTPException(
                status_code=403, 
                detail="This account is private. Follow to view profile."
            )
    
    # Get stats (only show if public OR following OR owner)
    can_view_stats = user.is_public or is_following or is_owner
    
    if can_view_stats:
        posts_count_result = await db.execute(
            select(func.count()).select_from(Post).where(Post.user_id == user_id)
        )
        posts_count = posts_count_result.scalar()
        
        followers_count_result = await db.execute(
            select(func.count()).select_from(Follow).where(Follow.following_id == user_id)
        )
        followers_count = followers_count_result.scalar()
        
        following_count_result = await db.execute(
            select(func.count()).select_from(Follow).where(Follow.follower_id == user_id)
        )
        following_count = following_count_result.scalar()
        
        active_stories_result = await db.execute(
            select(func.count()).select_from(Story)
            .where(Story.user_id == user_id)
            .where(Story.expires_at > datetime.utcnow())
        )
        active_stories_count = active_stories_result.scalar()
        
        # Check if current user follows this profile
        follow_status_result = await db.execute(
            select(Follow).where(
                and_(
                    Follow.follower_id == current_user.id,
                    Follow.following_id == user_id
                )
            )
        )
        follows_back = follow_status_result.scalar_one_or_none() is not None
    else:
        posts_count = 0
        followers_count = 0
        following_count = 0
        active_stories_count = 0
        follows_back = False
    
    return {
        **user.__dict__,
        "posts_count": posts_count,
        "followers_count": followers_count,
        "following_count": following_count,
        "active_stories_count": active_stories_count,
        "is_following": follows_back if not is_owner else None
    }

@router.patch("/me/profile-photo")
async def update_profile_photo(
    profile_photo_url: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update profile photo URL"""
    
    current_user.profile_photo_url = profile_photo_url
    current_user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(current_user)
    
    return {
        "message": "Profile photo updated successfully",
        "profile_photo_url": current_user.profile_photo_url
    }

@router.patch("/me/privacy")
async def update_privacy(
    is_public: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Make account public or private"""
    
    current_user.is_public = is_public
    current_user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(current_user)
    
    status = "public" if is_public else "private"
    return {"message": f"Account is now {status}"}

@router.get("/search/")
async def search_users(
    query: str,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search users by username or email"""
    
    result = await db.execute(
        select(User)
        .where(
            (User.username.contains(query)) | (User.email.contains(query))
        )
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()
    
    # Filter private accounts (only show if current user follows them)
    visible_users = []
    for user in users:
        if user.id == current_user.id:
            visible_users.append(user)
        elif user.is_public:
            visible_users.append(user)
        else:
            # Check if following
            follow_check = await db.execute(
                select(Follow).where(
                    and_(
                        Follow.follower_id == current_user.id,
                        Follow.following_id == user.id
                    )
                )
            )
            if follow_check.scalar_one_or_none():
                visible_users.append(user)
    
    return {
        "query": query,
        "count": len(visible_users),
        "users": visible_users
    }

@router.delete("/me")
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete own account (soft delete or hard delete)"""
    
    # Hard delete - will cascade to posts, stories, follows due to cascade setting in models
    await db.delete(current_user)
    await db.commit()
    
    return {"message": "Account deleted successfully"}