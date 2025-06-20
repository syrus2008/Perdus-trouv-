# NOTE : Pour la gestion évolutive du schéma de base, il est recommandé d'utiliser Alembic pour les migrations.
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Boolean, UniqueConstraint, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# Railway attend une URL DATABASE_URL en postgresql+asyncpg://
if DATABASE_URL and not DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    username = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")  # 'user' or 'admin'

class ActionLog(Base):
    __tablename__ = "action_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String, nullable=False)
    object_type = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class ObjetTrouve(Base):
    __tablename__ = "objets_trouves"
    id = Column(String, primary_key=True, index=True)
    description = Column(String)
    date_rapport = Column(String)
    infos = Column(String)
    image = Column(String)
    rendu = Column(Boolean, default=False)
    nom_beneficiaire = Column(String, nullable=True)
    prenom_beneficiaire = Column(String, nullable=True)
    telephone_beneficiaire = Column(String, nullable=True)
    email_beneficiaire = Column(String, nullable=True, unique=True)
    photo_rendu = Column(String, nullable=True)

class ObjetPerdu(Base):
    __tablename__ = "objets_perdus"
    id = Column(String, primary_key=True, index=True)
    description = Column(String)
    date_rapport = Column(String)
    infos = Column(String)
    nom = Column(String)
    prenom = Column(String)
    telephone = Column(String)
    email = Column(String, unique=True)

class ComparaisonIgnoree(Base):
    __tablename__ = "comparaisons_ignorees"
    id = Column(String, primary_key=True, index=True)
    id_trouve = Column(String, nullable=False)
    id_perdu = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint("id_trouve", "id_perdu", name="_trouve_perdu_uc"),)

