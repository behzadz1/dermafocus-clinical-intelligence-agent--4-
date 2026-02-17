"""
Configuration Management for DermaAI CKPA Backend
Loads environment variables and provides type-safe configuration
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application Settings
    app_name: str = Field(default="DermaAI CKPA API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=4, alias="WORKERS")
    
    # CORS Settings
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS"
    )
    
    # API Keys - AI Services
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    pinecone_api_key: str = Field(default="", alias="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-east-1", alias="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="dermaai-ckpa", alias="PINECONE_INDEX_NAME")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/dermaai_db",
        alias="DATABASE_URL"
    )
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    
    # Security
    secret_key: str = Field(
        default="change-this-to-a-random-secret-key-in-production",
        alias="SECRET_KEY"
    )
    api_key_header: str = Field(default="X-API-Key", alias="API_KEY_HEADER")
    valid_api_keys: str = Field(default="", alias="VALID_API_KEYS")  # Comma-separated list of valid API keys
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, alias="RATE_LIMIT_PER_HOUR")
    
    # Document Processing
    max_upload_size: int = Field(default=52428800, alias="MAX_UPLOAD_SIZE")  # 50MB
    allowed_extensions: str = Field(
        default=".pdf,.docx,.txt,.mp4,.mov",
        alias="ALLOWED_EXTENSIONS"
    )
    upload_dir: str = Field(default="./data/uploads", alias="UPLOAD_DIR")
    processed_dir: str = Field(default="./data/processed", alias="PROCESSED_DIR")

    # Hierarchical Chunking Configuration
    use_hierarchical_chunking: bool = Field(
        default=True,
        alias="USE_HIERARCHICAL_CHUNKING"
    )

    # Clinical Paper chunking (hierarchical with parent-child)
    clinical_paper_parent_chunk_size: int = Field(
        default=2000,
        alias="CLINICAL_PAPER_PARENT_CHUNK_SIZE"
    )
    clinical_paper_child_chunk_size: int = Field(
        default=500,
        alias="CLINICAL_PAPER_CHILD_CHUNK_SIZE"
    )
    clinical_paper_child_overlap: int = Field(
        default=50,
        alias="CLINICAL_PAPER_CHILD_OVERLAP"
    )

    # Case Study chunking (adaptive)
    case_study_chunk_size: int = Field(
        default=800,
        alias="CASE_STUDY_CHUNK_SIZE"
    )
    case_study_overlap: int = Field(
        default=100,
        alias="CASE_STUDY_OVERLAP"
    )

    # Protocol chunking (step-aware)
    protocol_chunk_size: int = Field(
        default=600,
        alias="PROTOCOL_CHUNK_SIZE"
    )
    protocol_overlap: int = Field(
        default=50,
        alias="PROTOCOL_OVERLAP"
    )

    # Factsheet/Brochure chunking (section-based)
    factsheet_chunk_size: int = Field(
        default=400,
        alias="FACTSHEET_CHUNK_SIZE"
    )
    brochure_chunk_size: int = Field(
        default=500,
        alias="BROCHURE_CHUNK_SIZE"
    )

    # Minimum chunk size (applies to all strategies)
    min_chunk_size: int = Field(
        default=100,
        alias="MIN_CHUNK_SIZE"
    )
    
    # Vector Search Configuration
    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL"
    )
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")
    vector_search_top_k: int = Field(default=10, alias="VECTOR_SEARCH_TOP_K")
    rerank_top_k: int = Field(default=5, alias="RERANK_TOP_K")

    # Hybrid Retrieval Configuration
    hybrid_search_enabled: bool = Field(default=True, alias="HYBRID_SEARCH_ENABLED")
    bm25_enabled: bool = Field(default=True, alias="BM25_ENABLED")
    bm25_top_k: int = Field(default=20, alias="BM25_TOP_K")
    hybrid_vector_weight: float = Field(default=0.6, alias="HYBRID_VECTOR_WEIGHT")
    hybrid_bm25_weight: float = Field(default=0.4, alias="HYBRID_BM25_WEIGHT")
    reranker_enabled: bool = Field(default=True, alias="RERANKER_ENABLED")  # PHASE 4.0: Enabled by default for quality
    reranker_provider: str = Field(default="sentence_transformers", alias="RERANKER_PROVIDER")
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        alias="RERANKER_MODEL"
    )
    
    # Claude Configuration
    claude_model: str = Field(
        default="claude-sonnet-4-20250514",
        alias="CLAUDE_MODEL"
    )
    claude_max_tokens: int = Field(default=2000, alias="CLAUDE_MAX_TOKENS")
    claude_temperature: float = Field(default=0.2, alias="CLAUDE_TEMPERATURE")

    # Response Customization
    default_audience: str = Field(
        default="physician",
        alias="DEFAULT_AUDIENCE"
    )  # physician, nurse_practitioner, aesthetician, clinic_staff, patient
    default_response_style: str = Field(
        default="clinical",
        alias="DEFAULT_RESPONSE_STYLE"
    )  # clinical, conversational, concise, detailed, educational
    customizer_preset: str = Field(
        default="physician_clinical",
        alias="CUSTOMIZER_PRESET"
    )  # physician_clinical, physician_concise, nurse_practical, aesthetician_educational, staff_simple
    
    # Logging
    log_file: str = Field(default="./logs/app.log", alias="LOG_FILE")
    log_rotation: str = Field(default="500 MB", alias="LOG_ROTATION")
    log_retention: str = Field(default="30 days", alias="LOG_RETENTION")

    # Audit logging
    audit_log_enabled: bool = Field(default=True, alias="AUDIT_LOG_ENABLED")
    audit_log_file: str = Field(default="./logs/audit.log", alias="AUDIT_LOG_FILE")
    audit_log_max_bytes: int = Field(default=10_000_000, alias="AUDIT_LOG_MAX_BYTES")
    audit_log_backup_count: int = Field(default=5, alias="AUDIT_LOG_BACKUP_COUNT")
    
    # Monitoring (optional)
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    
    # Beta Testing Features
    enable_video_processing: bool = Field(default=False, alias="ENABLE_VIDEO_PROCESSING")
    enable_image_analysis: bool = Field(default=False, alias="ENABLE_IMAGE_ANALYSIS")
    enable_advanced_analytics: bool = Field(default=False, alias="ENABLE_ADVANCED_ANALYTICS")
    enable_keyframe_extraction: bool = Field(default=False, alias="ENABLE_KEYFRAME_EXTRACTION")
    video_keyframe_count: int = Field(default=8, alias="VIDEO_KEYFRAME_COUNT")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Parse allowed extensions string into list"""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]
    
    @property
    def embedding_dimension(self) -> int:
        """Alias for embedding_dimensions for consistency"""
        return self.embedding_dimensions
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"

    @property
    def chunking_config(self) -> dict:
        """Get chunking configuration by document type"""
        return {
            "clinical_paper": {
                "parent_chunk_size": self.clinical_paper_parent_chunk_size,
                "child_chunk_size": self.clinical_paper_child_chunk_size,
                "child_overlap": self.clinical_paper_child_overlap,
                "min_chunk_size": self.min_chunk_size
            },
            "case_study": {
                "chunk_size": self.case_study_chunk_size,
                "overlap": self.case_study_overlap,
                "min_chunk_size": self.min_chunk_size
            },
            "protocol": {
                "chunk_size": self.protocol_chunk_size,
                "overlap": self.protocol_overlap,
                "min_chunk_size": self.min_chunk_size
            },
            "factsheet": {
                "chunk_size": self.factsheet_chunk_size,
                "min_chunk_size": self.min_chunk_size
            },
            "brochure": {
                "chunk_size": self.brochure_chunk_size,
                "min_chunk_size": self.min_chunk_size
            }
        }


# Global settings instance
settings = Settings()


# Validate critical settings on import
def validate_settings():
    """Validate that critical settings are configured"""
    critical_keys = [
        "anthropic_api_key",
        "pinecone_api_key",
        "openai_api_key",
        "secret_key"
    ]
    
    missing_keys = []
    for key in critical_keys:
        value = getattr(settings, key)
        if not value or value == "your-key-here" or "change-in-production" in value:
            missing_keys.append(key.upper())
    
    if missing_keys and settings.is_production:
        raise ValueError(
            f"Missing critical configuration in production: {', '.join(missing_keys)}"
        )
    
    return True


# Run validation (will only raise error in production)
if settings.is_production:
    validate_settings()
