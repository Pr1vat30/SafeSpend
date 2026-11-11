"""Template ORM model. Copy to `app/models/<module>/<module>_model.py` and rename.

Map a table defined in `database/schema.sql`, then export the class from `app/models/__init__.py`.
"""

from app.models.common.base import Base


class TemplateModel(Base):
    __abstract__ = True  # remove when mapping a real table

    # __tablename__ = "<table_name>"
    # id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
