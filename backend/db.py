from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Boolean
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and not DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

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
    email_beneficiaire = Column(String, nullable=True)
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
    email = Column(String)
