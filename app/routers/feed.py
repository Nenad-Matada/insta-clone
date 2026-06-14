from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
from app.database import get_db
from app.models import User, Post, PostItem, Story, Follow
from app.schemas import PostResponse, StoryResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/feed", tags=["Feed"])

@router.get("/posts")
async def get_feed_posts(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get posts from users that current user follows (timeline feed)"""
    
    # Get list of users that current user follows
    following_result = await db.execute(
        select(Follow.following_id).where(Follow.follower_id == current_user.id)
    )
    following_ids = [row[0] for row in following_result.all()]
    
    # include own posts
    following_ids.append(current_user.id)
    
    if not following_ids:
        return {"posts": [], "message": "Follow some users to see posts"}
    
    # Get posts from followed users
    result = await db.execute(
        select(Post)
        .where(Post.user_id.in_(following_ids))
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
        
        # Get user info
        user_result = await db.execute(select(User).where(User.id == post.user_id))
        post.user = user_result.scalar_one_or_none()
    
    return {
        "posts": posts,
        "count": len(posts),
        "skip": skip,
        "limit": limit
    }

@router.get("/stories")
async def get_feed_stories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get active stories from users that current user follows"""
    
    # Get list of users that current user follows
    following_result = await db.execute(
        select(Follow.following_id).where(Follow.follower_id == current_user.id)
    )
    following_ids = [row[0] for row in following_result.all()]
    
    # Always include own stories
    following_ids.append(current_user.id)
    
    if not following_ids:
        return {"stories": [], "message": "Follow some users to see stories"}
    
    # Get active stories (not expired)
    current_time = datetime.utcnow()
    result = await db.execute(
        select(Story)
        .where(Story.user_id.in_(following_ids))
        .where(Story.expires_at > current_time)
        .order_by(desc(Story.created_at))
    )
    stories = result.scalars().all()
    
    # Group stories by user
    stories_by_user = {}
    for story in stories:
        if story.user_id not in stories_by_user:
            # Get user info
            user_result = await db.execute(select(User).where(User.id == story.user_id))
            user = user_result.scalar_one_or_none()
            stories_by_user[story.user_id] = {
                "user": user,
                "stories": []
            }
        stories_by_user[story.user_id]["stories"].append(story)
    
    return {
        "stories_by_user": stories_by_user,
        "total_stories": len(stories)
    }

@router.get("/combined")
async def get_combined_feed(
    posts_limit: int = 10,
    stories_limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get both posts and stories in one request"""
    
    # Get stories
    following_result = await db.execute(
        select(Follow.following_id).where(Follow.follower_id == current_user.id)
    )
    following_ids = [row[0] for row in following_result.all()]
    following_ids.append(current_user.id)
    
    current_time = datetime.utcnow()
    stories_result = await db.execute(
        select(Story)
        .where(Story.user_id.in_(following_ids))
        .where(Story.expires_at > current_time)
        .order_by(desc(Story.created_at))
        .limit(stories_limit)
    )
    stories = stories_result.scalars().all()
    
    # Get posts
    posts_result = await db.execute(
        select(Post)
        .where(Post.user_id.in_(following_ids))
        .order_by(desc(Post.created_at))
        .limit(posts_limit)
    )
    posts = posts_result.scalars().all()
    
    # Load items for posts
    for post in posts:
        items_result = await db.execute(
            select(PostItem).where(PostItem.post_id == post.id).order_by(PostItem.order)
        )
        post.items = items_result.scalars().all()
    
    return {
        "stories": stories,
        "posts": posts,
        "summary": {
            "stories_count": len(stories),
            "posts_count": len(posts)
        }
    }