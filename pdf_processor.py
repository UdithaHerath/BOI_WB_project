# CORRECT IMPORTS
import pdfplumber  # Fixed typo
import re
import pandas as pd
from database import Session, Employee, Contribution


def extract_employee_data(pdf_path):
    all_employees = []
    year, month = None, None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            # Extract report period
            if not year:
                date_match = re.search(r"Salary Month (\d{4}) / (\w+)", text)
                if date_match:
                    year, month = int(date_match.group(1)), date_match.group(2)

            # Process text line by line
            for line in text.split('\n'):
                # Skip header/footer lines
                if "EMPLOYEE SALARY COMPONENT REPORT" in line:
                    continue
                if "National Water" in line:
                    continue
                if "Page" in line and "of" in line:
                    continue

                # Match employee data lines
                emp_match = re.match(r"^(\d{4,})\s+(.+?)\s+([A-Z][\w\s\.\-\(\)]+)\s+([\d,]+\.\d{2})$", line)
                if emp_match:
                    emp_number = emp_match.group(1).strip()
                    designation = emp_match.group(2).strip()
                    name = emp_match.group(3).strip()
                    amount = float(emp_match.group(4).replace(",", ""))

                    all_employees.append({
                        "emp_number": emp_number,
                        "name": name,
                        "designation": designation,
                        "amount": amount
                    })
                else:
                    # Try alternative pattern for lines without designation
                    alt_match = re.match(r"^(\d{4,})\s+([A-Z][\w\s\.\-\(\)]+)\s+([\d,]+\.\d{2})$", line)
                    if alt_match:
                        emp_number = alt_match.group(1).strip()
                        name = alt_match.group(2).strip()
                        amount = float(alt_match.group(3).replace(",", ""))

                        all_employees.append({
                            "emp_number": emp_number,
                            "name": name,
                            "designation": "N/A",
                            "amount": amount
                        })

    return {
        "year": year,
        "month": month,
        "employees": all_employees
    }


def save_to_database(data):
    session = Session()
    try:
        for emp in data["employees"]:
            # Update employee master
            employee = session.query(Employee).filter_by(emp_number=emp["emp_number"]).first()
            if not employee:
                employee = Employee(
                    emp_number=emp["emp_number"],
                    name=emp["name"],
                    designation=emp["designation"]
                )
                session.add(employee)

            # Add contribution
            contribution = Contribution(
                emp_number=emp["emp_number"],
                year=data["year"],
                month=data["month"],
                amount=emp["amount"]
            )
            session.add(contribution)

        session.commit()
        print(f"✅ Saved {len(data['employees'])} records for {data['month']} {data['year']}")  # CORRECTED LINE
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {str(e)}")
    finally:
        session.close()


if __name__ == "__main__":
    # Test extraction
    pdf_path = "05.pdf"  # Replace with your PDF
    report_data = extract_employee_data(pdf_path)

    print(f"Report: {report_data['year']}-{report_data['month']}")
    print(f"Found {len(report_data['employees'])} employees")  # FIXED THIS LINE

    # Save to DB
    save_to_database(report_data)