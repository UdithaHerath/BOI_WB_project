from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from database import Session, Employee, Contribution, Loan, EmployeeDocument
import os
from datetime import datetime
from pdf_processor import extract_employee_data, save_to_database
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Create uploads directory if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Add after UPLOAD_FOLDER config
app.config['EMPLOYEE_DOCUMENTS_FOLDER'] = 'employee_documents'
os.makedirs(app.config['EMPLOYEE_DOCUMENTS_FOLDER'], exist_ok=True)


# Home Page - Document Upload & Search
@app.route('/')
def index():
    return render_template('index.html')


# Document Upload Handler
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)

    if file and file.filename.endswith('.pdf'):
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Process PDF and save to database
        report_data = extract_employee_data(file_path)
        save_to_database(report_data)

        return redirect(url_for('documents'))

    return redirect(request.url)


# Update the employee_dashboard route
@app.route('/employee')
def employee_dashboard():
    emp_number = request.args.get('emp_number')
    if not emp_number:
        return redirect(url_for('index'))

    session = Session()
    try:
        employee = session.query(Employee).options(
            joinedload(Employee.documents)
        ).filter_by(emp_number=emp_number).first()

        if not employee:
            return "Employee not found", 404

        # Get contributions grouped by year
        contributions = session.query(Contribution).filter_by(emp_number=emp_number).all()
        contributions_by_year = {}
        for contrib in contributions:
            if contrib.year not in contributions_by_year:
                contributions_by_year[contrib.year] = {}
            contributions_by_year[contrib.year][contrib.month] = contrib.amount

        # Get loans
        loans = session.query(Loan).filter_by(emp_number=emp_number).all()

        return render_template('dashboard.html',
                               employee=employee,
                               contributions=contributions_by_year,
                               loans=loans)
    finally:
        session.close()


# Add Loan
@app.route('/add_loan', methods=['POST'])
def add_loan():
    emp_number = request.form['emp_number']
    loan_number = request.form['loan_number']
    loan_date = datetime.strptime(request.form['loan_date'], '%Y-%m-%d').date()
    loan_amount = float(request.form['loan_amount'])
    due_amount = float(request.form['due_amount'])
    check_number = request.form['check_number']

    session = Session()
    new_loan = Loan(
        emp_number=emp_number,
        loan_number=loan_number,
        loan_date=loan_date,
        loan_amount=loan_amount,
        due_amount=due_amount,
        check_number=check_number
    )
    session.add(new_loan)
    session.commit()
    session.close()

    return redirect(url_for('employee_dashboard', emp_number=emp_number))


# Document Library
@app.route('/documents')
def documents():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('documents.html', files=files)


# Download Document
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ===== NEW LOAN MANAGEMENT ROUTES =====
# Loan Filter Page
@app.route('/loans')
def loans_page():
    return render_template('loans.html')


# Loan Filter Results
@app.route('/filter_loans', methods=['POST'])
def filter_loans():
    try:
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD", 400

    session = Session()

    # Get loans in date range with employee info
    loans = session.query(Loan, Employee).join(
        Employee, Employee.emp_number == Loan.emp_number
    ).filter(
        Loan.loan_date.between(start_date, end_date)
    ).all()

    session.close()

    return render_template('loan_results.html',
                           loans=loans,
                           start_date=start_date,
                           end_date=end_date)


# Update the upload_employee_document function
@app.route('/upload_employee_document/<emp_number>', methods=['POST'])
def upload_employee_document(emp_number):
    if 'document' not in request.files:
        return redirect(url_for('employee_dashboard', emp_number=emp_number))

    file = request.files['document']
    if file.filename == '':
        return redirect(url_for('employee_dashboard', emp_number=emp_number))

    if file:
        # Secure filename and create unique path
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        save_path = os.path.join(app.config['EMPLOYEE_DOCUMENTS_FOLDER'], unique_filename)
        file.save(save_path)

        # Save to database
        session = Session()
        try:
            new_doc = EmployeeDocument(
                emp_number=emp_number,
                document_name=filename,
                file_path=unique_filename
            )
            session.add(new_doc)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error saving document: {str(e)}")
        finally:
            session.close()

    return redirect(url_for('employee_dashboard', emp_number=emp_number))


# Employee Document Download
@app.route('/download_employee_document/<filename>')
def download_employee_document(filename):
    return send_from_directory(
        app.config['EMPLOYEE_DOCUMENTS_FOLDER'],
        filename,
        as_attachment=True
    )


# ===== END NEW ROUTES =====

if __name__ == '__main__':
    app.run(debug=True)