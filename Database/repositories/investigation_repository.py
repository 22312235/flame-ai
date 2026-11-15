import uuid
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.investigation import Investigation


class InvestigationRepository:
    """
    Handles database operations for investigations.

    This repository does not commit transactions.
    Transaction management is handled by the caller.
    """

    # =====================================================
    # CREATE
    # =====================================================

    @staticmethod
    def create(
        db: Session,
        title: str,
        external_id: str | None = None,
        description: str | None = None,
        principal_investigator: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        metadata: dict | None = None,
    ) -> Investigation:
        """
        Creates and registers a new investigation.
        """

        investigation = Investigation(
            title=title,
            external_id=external_id,
            description=description,
            principal_investigator=principal_investigator,
            start_date=start_date,
            end_date=end_date,
            metadata_json=metadata or {},
        )

        db.add(investigation)
        db.flush()

        return investigation

    # =====================================================
    # READ
    # =====================================================

    @staticmethod
    def get_by_id(
        db: Session,
        investigation_id: uuid.UUID,
    ) -> Investigation | None:
        """
        Retrieves an investigation using its UUID.
        """

        return db.get(Investigation, investigation_id)

    @staticmethod
    def get_by_external_id(
        db: Session,
        external_id: str,
    ) -> Investigation | None:
        """
        Retrieves an investigation using its NASA/PSI ID.
        """

        statement = select(Investigation).where(
            Investigation.external_id == external_id
        )

        return db.scalar(statement)

    @staticmethod
    def get_all(
        db: Session,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Investigation]:
        """
        Retrieves investigations with pagination.

        Newest investigations are returned first.
        """

        if limit < 1:
            raise ValueError("limit must be greater than zero.")

        if offset < 0:
            raise ValueError("offset cannot be negative.")

        statement = (
            select(Investigation)
            .order_by(Investigation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(db.scalars(statement).all())

    # =====================================================
    # COUNT
    # =====================================================

    @staticmethod
    def count(db: Session) -> int:
        """
        Returns the total number of investigations.
        """

        statement = select(func.count()).select_from(Investigation)

        return db.scalar(statement) or 0

    # =====================================================
    # EXISTS
    # =====================================================

    @staticmethod
    def exists(
        db: Session,
        investigation_id: uuid.UUID,
    ) -> bool:
        """
        Checks whether an investigation exists.
        """

        statement = select(
            select(Investigation.investigation_id)
            .where(
                Investigation.investigation_id == investigation_id
            )
            .exists()
        )

        return bool(db.scalar(statement))

    # =====================================================
    # UPDATE
    # =====================================================

    @staticmethod
    def update(
        db: Session,
        investigation_id: uuid.UUID,
        **updates,
    ) -> Investigation | None:
        """
        Updates an existing investigation.

        Only explicitly permitted fields can be modified.
        """

        allowed_fields = {
            "external_id",
            "title",
            "description",
            "principal_investigator",
            "start_date",
            "end_date",
            "metadata_json",
        }

        invalid_fields = set(updates) - allowed_fields

        if invalid_fields:
            raise ValueError(
                f"Invalid investigation fields: "
                f"{', '.join(sorted(invalid_fields))}"
            )

        investigation = InvestigationRepository.get_by_id(
            db,
            investigation_id,
        )

        if investigation is None:
            return None

        for field, value in updates.items():
            setattr(investigation, field, value)

        db.flush()

        return investigation

    # =====================================================
    # DELETE
    # =====================================================

    @staticmethod
    def delete(
        db: Session,
        investigation_id: uuid.UUID,
    ) -> bool:
        """
        Deletes an investigation.

        Its associated files and processing jobs are
        deleted through the database foreign-key cascades.
        """

        investigation = InvestigationRepository.get_by_id(
            db,
            investigation_id,
        )

        if investigation is None:
            return False

        db.delete(investigation)
        db.flush()

        return True