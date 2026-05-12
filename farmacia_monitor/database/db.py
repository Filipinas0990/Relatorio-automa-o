from sqlalchemy import (
    create_engine, Column, Integer, String, Numeric,
    Boolean, DateTime, Date, ForeignKey, CheckConstraint, text
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://farmacia:farmacia123@localhost:5432/farmacia_monitor"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Farmacia(Base):
    __tablename__ = "farmacias"

    id        = Column(Integer, primary_key=True)
    nome      = Column(String(120), nullable=False)
    url_base  = Column(String(255), nullable=False)
    email     = Column(String(120), nullable=False)
    ativa     = Column(Boolean, default=True)
    criado_em = Column(DateTime(timezone=True), default=datetime.utcnow)

    coletas = relationship("Coleta", back_populates="farmacia", cascade="all, delete")


class Coleta(Base):
    __tablename__ = "coletas"

    id                       = Column(Integer, primary_key=True)
    farmacia_id              = Column(Integer, ForeignKey("farmacias.id", ondelete="CASCADE"), nullable=False)
    data_coleta              = Column(DateTime(timezone=True), default=datetime.utcnow)
    periodo_inicio           = Column(Date, nullable=False)
    periodo_fim              = Column(Date, nullable=False)

    # 4 badges principais do dashboard
    aguardando_atendimento   = Column(Integer, default=0)
    em_andamento             = Column(Integer, default=0)
    atendimentos_finalizados = Column(Integer, default=0)
    total_atendimentos       = Column(Integer, default=0)
    # métricas extras
    vendas_realizadas        = Column(Integer, default=0)
    vendas_nao_realizadas    = Column(Integer, default=0)
    receita_total            = Column(Numeric(12, 2), default=0)

    taxa_conversao           = Column(Numeric(6, 2), default=0)
    variacao_receita         = Column(Numeric(8, 2), default=0)
    variacao_atendimentos    = Column(Numeric(8, 2), default=0)
    variacao_vendas          = Column(Numeric(8, 2), default=0)

    score_criticidade        = Column(Numeric(5, 2), default=0)
    nivel_alerta             = Column(
        String(10), default="verde",
        nullable=False
    )
    __table_args__ = (
        CheckConstraint("nivel_alerta IN ('verde', 'amarelo', 'vermelho')", name="chk_nivel_alerta"),
    )

    farmacia  = relationship("Farmacia", back_populates="coletas")
    canais    = relationship("ColetaCanal", back_populates="coleta", cascade="all, delete")
    conexoes  = relationship("ColetaConexao", back_populates="coleta", cascade="all, delete")


class ColetaCanal(Base):
    __tablename__ = "coleta_canais"

    id           = Column(Integer, primary_key=True)
    coleta_id    = Column(Integer, ForeignKey("coletas.id", ondelete="CASCADE"), nullable=False)
    canal        = Column(String(80), nullable=False)
    atendimentos = Column(Integer, default=0)
    vendas       = Column(Integer, default=0)

    coleta = relationship("Coleta", back_populates="canais")


class ColetaConexao(Base):
    __tablename__ = "coleta_conexoes"

    id           = Column(Integer, primary_key=True)
    coleta_id    = Column(Integer, ForeignKey("coletas.id", ondelete="CASCADE"), nullable=False)
    conexao      = Column(String(120), nullable=False)
    atendimentos = Column(Integer, default=0)
    vendas       = Column(Integer, default=0)

    coleta = relationship("Coleta", back_populates="conexoes")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
