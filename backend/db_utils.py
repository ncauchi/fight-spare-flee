from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import sqlalchemy as sql
from datetime import datetime
import os
import asyncio

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(sql.String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(sql.String(255))

async def create_user(username: str, password_hash: str) -> User:
    async with SessionLocal() as session:
        user = User(username=username, password_hash=password_hash)
        session.add(user)
        await session.commit()
        return user
    
async def get_user_by_username(username: str) -> User | None:
    async with SessionLocal() as session:
        result = await session.execute(
            sql.select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    

async def init_db(retries=5, delay=2):
    for attempt in range(retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(sql.text("SELECT 1"))
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception:
            if attempt < retries - 1:
                print(f"Database not ready, retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                raise

async def teardown_db():
    await engine.dispose()