# database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    emp_number = Column(String(20), unique=True)
    name = Column(String(100))
    designation = Column(String(100))


class Contribution(Base):
    __tablename__ = 'contributions'
    id = Column(Integer, primary_key=True)
    emp_number = Column(String(20))
    year = Column(Integer)
    month = Column(String(10))
    amount = Column(Float)


class Loan(Base):
    __tablename__ = 'loans'
    id = Column(Integer, primary_key=True)
    emp_number = Column(String(20))
    loan_number = Column(String(50))
    loan_date = Column(Date)
    loan_amount = Column(Float)
    due_amount = Column(Float)
    check_number = Column(String(50))


# ===== NEW EMPLOYEE DOCUMENT MODEL =====
class EmployeeDocument(Base):
    __tablename__ = 'employee_documents'
    id = Column(Integer, primary_key=True)
    emp_number = Column(String(20), ForeignKey('employees.emp_number'))
    document_name = Column(String(100))
    file_path = Column(String(200))
    upload_date = Column(Date, default=datetime.now)

    employee = relationship("Employee", backref="documents")


# ===== END NEW MODEL =====

# Initialize SQLite database
engine = create_engine('sqlite:///fund_tracker.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)