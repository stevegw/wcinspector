"""
WCInspector - Database Models and Connection
SQLite database for storing questions, answers, scraped pages, and settings
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), "wcinspector.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class Question(Base):
    """Model for storing user questions"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    category = Column(String(100))  # windchill, creo, codebeamer, etc.
    detected_topic = Column(String(200))  # AI-detected topic for grouping
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to answers
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class Answer(Base):
    """Model for storing AI-generated answers"""
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_text = Column(Text, nullable=False)
    pro_tips = Column(JSON, default=list)  # List of pro tips
    source_links = Column(JSON, default=list)  # List of PTC documentation URLs
    related_qa_ids = Column(JSON, default=list)  # List of related question IDs
    created_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String(100))
    tone_setting = Column(String(50))
    length_setting = Column(String(50))

    # Relationship to question
    question = relationship("Question", back_populates="answers")


class ScrapedPage(Base):
    """Model for storing scraped PTC documentation pages"""
    __tablename__ = "scraped_pages"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), unique=True, nullable=False)
    title = Column(String(500))
    content = Column(Text)
    section = Column(String(200))
    topic = Column(String(200))
    category = Column(String(100), default="windchill")  # windchill, creo, etc.
    scraped_at = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String(64))  # SHA-256 hash for detecting changes

    # Relationship to images
    images = relationship("ScrapedImage", back_populates="page", cascade="all, delete-orphan")
    # Relationship to course items
    course_items = relationship("CourseItem", back_populates="page")


class ScrapedImage(Base):
    """Model for storing images extracted from scraped pages"""
    __tablename__ = "scraped_images"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("scraped_pages.id"), nullable=False)
    url = Column(String(1000), nullable=False)
    alt_text = Column(Text)
    caption = Column(Text)
    context_before = Column(Text)  # Text before the image
    context_after = Column(Text)   # Text after the image
    ai_caption = Column(Text)      # AI-generated caption (optional)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to page
    page = relationship("ScrapedPage", back_populates="images")


# Documentation categories configuration
DOC_CATEGORIES = {
    "windchill": {
        "name": "Windchill",
        "base_url": "https://support.ptc.com/help/windchill/r13.1.2.0/en/",
        "description": "PTC Windchill PLM Documentation"
    },
    "creo": {
        "name": "Creo",
        "base_url": "https://support.ptc.com/help/creo/creo_pma/r12/usascii/",
        "description": "PTC Creo Parametric Documentation"
    },
    "community-windchill": {
        "name": "Windchill Community",
        "base_url": "https://community.ptc.com/t5/Windchill/bd-p/Windchill",
        "description": "PTC Community Windchill Discussions"
    },
    "community-creo": {
        "name": "Creo Community",
        "base_url": "https://community.ptc.com/t5/Creo-Parametric/bd-p/crlounge",
        "description": "PTC Community Creo Discussions"
    }
}


class ScrapeStats(Base):
    """Model for storing scraping statistics"""
    __tablename__ = "scrape_stats"

    id = Column(Integer, primary_key=True, index=True)
    last_full_scrape = Column(DateTime)
    last_partial_scrape = Column(DateTime)
    total_pages = Column(Integer, default=0)
    total_articles = Column(Integer, default=0)
    scrape_duration = Column(Integer)  # Duration in seconds


class Setting(Base):
    """Model for storing user settings"""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ErrorLog(Base):
    """Model for storing error logs"""
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True)
    error_type = Column(String(100))
    message = Column(Text)
    stack_trace = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Course(Base):
    """Model for storing learning courses/playlists"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # Optional grouping
    current_item_id = Column(Integer)  # Resume position (item id)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to course items
    items = relationship("CourseItem", back_populates="course",
                        cascade="all, delete-orphan", order_by="CourseItem.position")


class CourseItem(Base):
    """Model for storing items within a course"""
    __tablename__ = "course_items"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    page_id = Column(Integer, ForeignKey("scraped_pages.id"), nullable=False)
    position = Column(Integer, nullable=False)  # Order in course
    instructor_notes = Column(Text)  # Notes from course creator
    learner_notes = Column(Text)  # Personal notes while learning
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    quiz_answer = Column(Integer)  # For quiz questions: index of selected answer (0-3)
    quiz_correct = Column(Boolean)  # Whether the quiz answer was correct

    # Relationships
    course = relationship("Course", back_populates="items")
    page = relationship("ScrapedPage", back_populates="course_items")


# Available user roles by category
USER_ROLES = {
    "PLM": ["PLM Admin", "Change Analyst", "Product Manager", "BOM Specialist"],
    "CAD": ["CAD Designer", "CAD Admin", "Manufacturing Engineer"],
    "ALM": ["ALM Admin", "Requirements Analyst", "Test Engineer", "Developer"]
}


class UserProfile(Base):
    """Model for storing user profile and preferences"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(100))
    role = Column(String(100))  # One of the USER_ROLES values
    role_category = Column(String(50))  # PLM, CAD, or ALM
    interests = Column(JSON, default=list)  # Array of topic interests
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Default settings
DEFAULT_SETTINGS = {
    "theme": "light",
    "ai_tone": "technical",
    "response_length": "detailed",
    "ollama_model": "llama3:8b",
    "llm_provider": "groq",
    "groq_model": "llama-3.1-8b-instant"
}


def init_db():
    """Initialize the database - create all tables"""
    Base.metadata.create_all(bind=engine)

    # Run migrations for new columns
    from sqlalchemy import text
    with engine.connect() as conn:
        # Check if quiz_answer column exists in course_items
        result = conn.execute(text("PRAGMA table_info(course_items)"))
        columns = [row[1] for row in result.fetchall()]

        if 'quiz_answer' not in columns:
            conn.execute(text("ALTER TABLE course_items ADD COLUMN quiz_answer INTEGER"))
            conn.commit()

        if 'quiz_correct' not in columns:
            conn.execute(text("ALTER TABLE course_items ADD COLUMN quiz_correct BOOLEAN"))
            conn.commit()

        # Migration for Question categorization columns
        result = conn.execute(text("PRAGMA table_info(questions)"))
        question_columns = [row[1] for row in result.fetchall()]

        if 'category' not in question_columns:
            conn.execute(text("ALTER TABLE questions ADD COLUMN category VARCHAR(100)"))
            conn.commit()

        if 'detected_topic' not in question_columns:
            conn.execute(text("ALTER TABLE questions ADD COLUMN detected_topic VARCHAR(200)"))
            conn.commit()

    # Initialize default settings
    db = SessionLocal()
    try:
        for key, value in DEFAULT_SETTINGS.items():
            existing = db.query(Setting).filter(Setting.key == key).first()
            if not existing:
                setting = Setting(key=key, value=value)
                db.add(setting)
        db.commit()
    finally:
        db.close()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print(f"Database initialized at: {DB_PATH}")
