"""
Database Models (SQLAlchemy ORM)

These classes represent database tables.
Each class = one table in PostgreSQL.

Interview Q: "Walk me through your database schema."
Answer: "I have 5 tables: Users for authentication, Subscriptions for alert
preferences, PriceHistory for time-series price data, SentimentHistory for
analyzed news, and Alerts for generated divergence alerts. Foreign keys link
users to their subscriptions and alerts."
"""

from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """
    User accounts.
    
    Why a Users table?
    - Track who subscribes to what
    - Rate limiting per user
    - Alert history per user
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships - SQLAlchemy automatically handles JOINs
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Subscription(Base):
    """
    User subscriptions to stock alerts.
    
    One user can subscribe to many stocks.
    """
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String(10), nullable=False, index=True)
    alert_threshold = Column(Float, default=0.5)  # Min divergence severity
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="subscriptions")
    
    __table_args__ = (
        Index('idx_user_ticker', 'user_id', 'ticker'),
    )
    
    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, ticker={self.ticker})>"


class PriceHistory(Base):
    """
    Historical stock prices (time-series data).
    
    Why store history?
    - Calculate price changes over time
    - Detect trends
    - Backtesting
    """
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    price = Column(Float, nullable=False)
    change_percent = Column(Float)
    volume = Column(BigInteger)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Index for fast time-series queries
    __table_args__ = (
        Index('idx_ticker_timestamp', 'ticker', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<PriceHistory(ticker={self.ticker}, price={self.price})>"


class SentimentHistory(Base):
    """
    Historical sentiment scores from news articles.
    
    Stores individual articles so we can:
    - Trace which news triggered alerts
    - Calculate aggregate sentiment
    - Audit/debug
    """
    __tablename__ = "sentiment_history"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    headline = Column(Text, nullable=False)
    source = Column(String(100))
    published_at = Column(DateTime(timezone=True))
    sentiment_score = Column(Float, nullable=False)  # -1 to +1
    sentiment_label = Column(String(20), nullable=False)  # positive/negative/neutral
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_ticker_created', 'ticker', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Sentiment(ticker={self.ticker}, score={self.sentiment_score})>"


class Alert(Base):
    """
    Generated alerts when divergences detected.
    
    Stores alert history for:
    - User notification
    - Analytics
    - Backtesting accuracy
    """
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String(10), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # "bullish_divergence" or "bearish_divergence"
    price = Column(Float, nullable=False)
    price_change = Column(Float, nullable=False)
    sentiment_score = Column(Float, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="alerts")
    
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Alert(ticker={self.ticker}, type={self.alert_type})>"


# Database connection setup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency injection for database sessions.
    
    FastAPI calls this to get a DB session for each request.
    Automatically closes session after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in database."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
