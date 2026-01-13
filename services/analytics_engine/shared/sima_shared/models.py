from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base

# Optional: vector embeddings for RAG (requires pgvector python package)
try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except Exception:  # pragma: no cover
    Vector = None

class Institution(Base):
    __tablename__ = "institutions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # admin, authority_admin, studio_director, reviewer, office_admin, owner
    institution_id: Mapped[str] = mapped_column(String, ForeignKey("institutions.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    institution_id: Mapped[str] = mapped_column(String, ForeignKey("institutions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    location_wkt: Mapped[str] = mapped_column(Text, nullable=True)
    region: Mapped[str] = mapped_column(String, nullable=True)
    style: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="DRAFT")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ProjectVersion(Base):
    __tablename__ = "project_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    guidelines_version_id: Mapped[str] = mapped_column(String, nullable=True)
    ruleset_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class FileObject(Base):
    __tablename__ = "files"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_version_id: Mapped[str] = mapped_column(String, ForeignKey("project_versions.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # ifc, facade_image, report, evidence
    filename: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class GuidelineVersion(Base):
    __tablename__ = "guideline_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)  # architsaudi
    region: Mapped[str] = mapped_column(String, nullable=True)
    url: Mapped[str] = mapped_column(String, nullable=True)
    pdf_url: Mapped[str] = mapped_column(String, nullable=True)
    sha256: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class GuideItem(Base):
    __tablename__ = "guide_items"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    guideline_version_id: Mapped[str] = mapped_column(String, ForeignKey("guideline_versions.id"), nullable=False)
    ref: Mapped[str] = mapped_column(String, nullable=False)  # url#anchor OR pdf#p=..&b=..
    title: Mapped[str] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[dict] = mapped_column(JSON, default=dict)  # {style, stage, scope, project_type, enforceable}
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Ruleset(Base):
    __tablename__ = "rulesets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    guideline_version_id: Mapped[str] = mapped_column(String, ForeignKey("guideline_versions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    compiled_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

class Rule(Base):
    __tablename__ = "rules"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    ruleset_id: Mapped[str] = mapped_column(String, ForeignKey("rulesets.id"), nullable=False)
    ref: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)  # BLOCK/WARN/INFO
    check_type: Mapped[str] = mapped_column(String, nullable=False) # doc_present, facade_opening_ratio, ids_requirement, manual
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[dict] = mapped_column(JSON, default=dict)

class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_version_id: Mapped[str] = mapped_column(String, ForeignKey("project_versions.id"), nullable=False)
    ruleset_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="RUNNING")
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    evaluation_id: Mapped[str] = mapped_column(String, ForeignKey("evaluations.id"), nullable=False)
    verdict: Mapped[str] = mapped_column(String, nullable=False)  # APPROVE/REJECT/CLARIFY
    rationale: Mapped[str] = mapped_column(Text, nullable=True)
    trace: Mapped[dict] = mapped_column(JSON, default=dict)  # hash chain + references
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    actor_user_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=True)
    entity_id: Mapped[str] = mapped_column(String, nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ----------------------
# RAG / Chat provenance
# ----------------------

class RagChunk(Base):
    __tablename__ = "rag_chunks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    guideline_version_id: Mapped[str] = mapped_column(String, ForeignKey("guideline_versions.id"), nullable=False)
    guide_item_id: Mapped[str] = mapped_column(String, ForeignKey("guide_items.id"), nullable=False)
    ref: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    # Vector type is optional; if pgvector is not installed, services can fall back to lexical retrieval.
    embedding: Mapped[object] = mapped_column(Vector(1536) if Vector else JSON, nullable=True)  # type: ignore
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChatRun(Base):
    __tablename__ = "chat_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)  # refuse_no_evidence | extractive | rag
    answer: Mapped[str] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)  # retrieved chunks + scores + explainability
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ----------------------
# IoT (SensorThings-like)
# ----------------------

class IoTThing(Base):
    __tablename__ = "iot_things"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    location_wkt: Mapped[str] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IoTDatastream(Base):
    __tablename__ = "iot_datastreams"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    thing_id: Mapped[str] = mapped_column(String, ForeignKey("iot_things.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=True)
    observed_property: Mapped[str] = mapped_column(String, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IoTObservation(Base):
    __tablename__ = "iot_observations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    datastream_id: Mapped[str] = mapped_column(String, ForeignKey("iot_datastreams.id"), nullable=False)
    result_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ----------------------
# Digital Twin registry
# ----------------------

class TwinAsset(Base):
    __tablename__ = "twin_assets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_version_id: Mapped[str] = mapped_column(String, ForeignKey("project_versions.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # tileset | gltf | pointcloud | photogrammetry
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
