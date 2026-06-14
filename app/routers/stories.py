from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User, Story
from app.schemas import StoryCreate, StoryResponse
from app.dependencies import get_current_user
from app.utils.file_handling import generate_random_story_url
from typing import Optional

router = APIRouter(prefix="/stories", tags=["Stories"])

@router.post("/upload", response_model=StoryResponse)
async def upload_story(
    file: UploadFile = File(...),
    close_friends_list: Optional[str] = Form(None),  # Comma-separated user IDs
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a story - generates random URL, stores in DB"""
    
    # Generate random URL for the story
    random_url = generate_random_story_url(file.filename)
    
    # Set expiry to 24 hours from now
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Create story record
    new_story = Story(
        media_url=random_url,
        user_id=current_user.id,
        close_friends_list=close_friends_list,  # Will be parsed by teammates
        expires_at=expires_at
    )
    
    db.add(new_story)
    await db.commit()
    await db.refresh(new_story)
    
    # Note: Actual file saving will be handled by teammates
    # You're just storing the URL
    
    return new_story

@router.get("/", response_model=list[StoryResponse])
async def get_stories(
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get stories for a user (public stories only, or close friends if configured)"""
    
    target_user_id = user_id if user_id else current_user.id
    
    # Get user to check privacy
    result = await db.execute(select(User).where(User.id == target_user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check privacy
    if not user.is_public and user.id != current_user.id:
        # Check if current user follows this user
        from app.models import Follow
        follow_check = await db.execute(
            select(Follow).where(
                Follow.follower_id == current_user.id,
                Follow.following_id == target_user_id
            )
        )
        if not follow_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Private account - follow to view stories")
    
    # Get non-expired stories
    current_time = datetime.utcnow()
    result = await db.execute(
        select(Story)
        .where(Story.user_id == target_user_id)
        .where(Story.expires_at > current_time)
        .order_by(Story.created_at.desc())
    )
    stories = result.scalars().all()
    
    return stories

@router.delete("/{story_id}")
async def delete_story(
    story_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete your own story"""
    
    result = await db.execute(
        select(Story).where(Story.id == story_id)
    )
    story = result.scalar_one_or_none()
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if story.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your story")
    
    await db.delete(story)
    await db.commit()
    
    return {"message": "Story deleted successfully"}