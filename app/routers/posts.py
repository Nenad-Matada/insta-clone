from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from app.database import get_db
from app.models import User, Post, PostItem
from app.schemas import PostCreate, PostResponse, PostItemCreate
from app.dependencies import get_current_user
from app.utils.file_handling import generate_random_post_url

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("/create", response_model=PostResponse)
async def create_post(
    description: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),  # Multiple photos
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a post with multiple photos"""
    
    if not files:
        raise HTTPException(status_code=400, detail="At least one photo required")
    
    # Create post
    new_post = Post(
        description=description,
        user_id=current_user.id
    )
    db.add(new_post)
    await db.flush()  # Get post ID without committing
    
    # Create post items (one per photo)
    for index, file in enumerate(files):
        random_url = generate_random_post_url(file.filename)
        post_item = PostItem(
            media_url=random_url,
            post_id=new_post.id,
            order=index
        )
        db.add(post_item)
    
    await db.commit()
    await db.refresh(new_post)
    
    # Load items for response
    result = await db.execute(
        select(PostItem).where(PostItem.post_id == new_post.id).order_by(PostItem.order)
    )
    new_post.items = result.scalars().all()
    
    return new_post

@router.get("/", response_model=list[PostResponse])
async def get_posts(
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get posts for a user"""
    
    target_user_id = user_id if user_id else current_user.id
    
    # Check privacy
    result = await db.execute(select(User).where(User.id == target_user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_public and user.id != current_user.id:
        from app.models import Follow
        follow_check = await db.execute(
            select(Follow).where(
                Follow.follower_id == current_user.id,
                Follow.following_id == target_user_id
            )
        )
        if not follow_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Private account")
    
    # Get posts with items
    result = await db.execute(
        select(Post)
        .where(Post.user_id == target_user_id)
        .order_by(desc(Post.created_at))
        .offset(skip)
        .limit(limit)
    )
    posts = result.scalars().all()
    
    # Load items for each post
    for post in posts:
        items_result = await db.execute(
            select(PostItem).where(PostItem.post_id == post.id).order_by(PostItem.order)
        )
        post.items = items_result.scalars().all()
    
    return posts

@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete your own post"""
    
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your post")
    
    await db.delete(post)
    await db.commit()
    
    return {"message": "Post deleted successfully"}