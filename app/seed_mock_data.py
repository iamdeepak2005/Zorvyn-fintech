import random
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.financial_record import FinancialRecord, RecordType
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.idempotency_key import IdempotencyKey  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

def generate_mock_data(num_users=10, records_per_user=100):
    db = SessionLocal()
    try:
        logger.info(f"Generating {num_users} mock users...")
        users = []
        roles = [UserRole.ANALYST, UserRole.VIEWER]
        
        # Check if admin already exists to assign records to them as well
        admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if admin:
            users.append(admin)

        for i in range(num_users):
            email = f"mockuser{i}@example.com"
            existing = db.query(User).filter(User.email == email).first()
            if existing:
                users.append(existing)
            else:
                user = User(
                    name=f"Mock User {i}",
                    email=email,
                    password_hash=hash_password("password123"),
                    role=random.choice(roles),
                    is_active=True,
                )
                db.add(user)
                users.append(user)
        
        db.commit()
        for u in users:
            db.refresh(u)
            
        logger.info(f"Generating {(len(users)) * records_per_user} financial records...")
        
        categories_expense = ["Food", "Transport", "Entertainment", "Utilities", "Rent", "Healthcare", "Shopping"]
        categories_income = ["Salary", "Investment", "Freelance", "Gift", "Bonus"]
        
        start_date = datetime.now(timezone.utc).date() - timedelta(days=365)
        
        records = []
        for user in users:
            for i in range(records_per_user):
                rtype = random.choices([RecordType.INCOME, RecordType.EXPENSE], weights=[0.3, 0.7])[0]
                category = random.choice(categories_income) if rtype == RecordType.INCOME else random.choice(categories_expense)
                
                # Random amount between 10 and 5000 (Expense usually lower than income)
                if rtype == RecordType.EXPENSE:
                    amount = Decimal(random.uniform(10, 500)).quantize(Decimal("0.01"))
                else:
                    amount = Decimal(random.uniform(1000, 5000)).quantize(Decimal("0.01"))
                
                # Random date within last year
                r_date = start_date + timedelta(days=random.randint(0, 365))
                
                record = FinancialRecord(
                    user_id=user.id,
                    amount=amount,
                    type=rtype,
                    category=category,
                    date=r_date,
                    notes=f"Mock {category.lower()} record #{i}"
                )
                records.append(record)
                
        # Bulk insert for fast execution
        db.bulk_save_objects(records)
        db.commit()
        
        logger.info("Mock data generation successfully completed.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to generate mock data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    generate_mock_data(num_users=10, records_per_user=50) # Generates 500+ records
