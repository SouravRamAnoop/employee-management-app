import shutil
from pathlib import Path
from fastapi import FastAPI, File, Form, Depends, HTTPException, Request, status, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# --- DATABASE SETUP ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    department = Column(String)
    profile_pic = Column(String, default="default.png")

Base.metadata.create_all(bind=engine)

# --- FASTAPI APP SETUP ---
app = FastAPI(title="Employee Management System - SQL Version")

UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROUTES ---

@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    """Fetch all employees from the database and render homepage."""
    employees = db.query(Employee).all()
    # Explicitly using TemplateResponse with modern Starlette syntax
    return templates.TemplateResponse(request, "index.html", {"employees": employees})


@app.get("/employees/new")
def new_employee_form(request: Request):
    """Render the form to create a new employee."""
    return templates.TemplateResponse(request, "create_employee.html", {})


@app.post("/employees/new")
async def create_employee(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    department: str = Form(...),
    profile_pic: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Handle file upload, persist employee data into SQL database."""
    filename = "default.png"
    
    if profile_pic and profile_pic.filename:
        filename = f"{profile_pic.filename}"
        file_path = UPLOAD_DIR / filename
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(profile_pic.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
        finally:
            profile_pic.file.close()

    db_employee = Employee(
        name=name,
        email=email,
        department=department,
        profile_pic=filename
    )
    
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/employees/{employee_id}")
def employee_detail(request: Request, employee_id: int, db: Session = Depends(get_db)):
    """Fetch a specific employee by ID from the database."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return templates.TemplateResponse(request, "employee_detail.html", {"employee": employee})