"""用户认证服务"""
from datetime import datetime

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    real_name: str = None,
    agree_terms: bool = False,
) -> User:
    user = User(
        username=username,
        real_name=real_name,
        email=email,
        password_hash=hash_password(password),
        agreed_terms_at=datetime.utcnow() if agree_terms else None,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if user and verify_password(password, user.password_hash):
        return user
    return None


async def update_user_profile(
    db: AsyncSession,
    user_id: int,
    **kwargs,
) -> User | None:
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    for key, value in kwargs.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user
