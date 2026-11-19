import re
import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.modules.customers.models import Customer, CustomerConsent
from app.modules.privacy.models import PrivacyPolicy
from app.modules.users.models import User
from app.modules.users.repository import escape_like
from app.shared.identifiers import search_key
from app.shared.pagination import PageParams


class CustomerRepository:
    """All queries are scoped to an organization."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> Customer | None:
        return self._session.scalar(
            select(Customer).where(
                Customer.id == customer_id, Customer.organization_id == organization_id
            )
        )

    def get_for_update(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> Customer | None:
        return self._session.scalar(
            select(Customer)
            .where(Customer.id == customer_id, Customer.organization_id == organization_id)
            .with_for_update()
        )

    def find_by_document(
        self,
        organization_id: uuid.UUID,
        id_type: str,
        id_number: str,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> Customer | None:
        query = select(Customer).where(
            Customer.organization_id == organization_id,
            Customer.id_type == id_type,
            Customer.id_number == id_number,
        )
        if exclude_id is not None:
            query = query.where(Customer.id != exclude_id)
        return self._session.scalar(query)

    def search(
        self,
        organization_id: uuid.UUID,
        params: PageParams,
        *,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Customer], int]:
        query: Select[Customer] = select(Customer).where(
            Customer.organization_id == organization_id
        )
        if search and search.strip():
            text = search.strip()
            conditions = [
                Customer.search_name.ilike(f"%{escape_like(search_key(text))}%", escape="\\")
            ]
            compact = re.sub(r"[\s.\-]", "", text)
            if compact:
                conditions.append(Customer.id_number.ilike(f"{escape_like(compact)}%", escape="\\"))
            if compact.lstrip("+").isdigit() and len(compact.lstrip("+")) >= 4:
                conditions.append(Customer.phone.like(f"%{compact.lstrip('+')}%"))
            query = query.where(or_(*conditions))
        if is_active is not None:
            query = query.where(Customer.is_active == is_active)

        total = self._session.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self._session.scalars(
            query.order_by(Customer.search_name, Customer.id)
            .offset(params.offset)
            .limit(params.size)
        ).all()
        return [*items], total

    def add(self, customer: Customer) -> None:
        self._session.add(customer)
        self._session.flush()

    # --- Consents -----------------------------------------------------------------------

    def add_consent(self, consent: CustomerConsent) -> None:
        self._session.add(consent)
        self._session.flush()

    def consent_history(
        self, customer_id: uuid.UUID
    ) -> list[tuple[CustomerConsent, int, str | None]]:
        rows = self._session.execute(
            select(CustomerConsent, PrivacyPolicy.version, User.full_name)
            .join(PrivacyPolicy, PrivacyPolicy.id == CustomerConsent.policy_id)
            .outerjoin(User, User.id == CustomerConsent.recorded_by_id)
            .where(CustomerConsent.customer_id == customer_id)
            .order_by(CustomerConsent.recorded_at.desc(), CustomerConsent.id.desc())
        ).all()
        return [(consent, version, name) for consent, version, name in rows]

    def current_consents(self, customer_id: uuid.UUID) -> list[tuple[CustomerConsent, int]]:
        """Most recent record of each purpose."""
        rows = self._session.execute(
            select(CustomerConsent, PrivacyPolicy.version)
            .join(PrivacyPolicy, PrivacyPolicy.id == CustomerConsent.policy_id)
            .where(CustomerConsent.customer_id == customer_id)
            .order_by(
                CustomerConsent.purpose,
                CustomerConsent.recorded_at.desc(),
                CustomerConsent.id.desc(),
            )
            .ext(distinct_on(CustomerConsent.purpose))
        ).all()
        return [(consent, version) for consent, version in rows]
