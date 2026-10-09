from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, func, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone, date
from typing import Optional
from pathlib import Path
import os, secrets, csv, io, json, uuid, hashlib, urllib.request, urllib.error, hmac, smtplib, ssl
from email.message import EmailMessage

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
FRONT = ROOT / 'frontend'
MEDIA = ROOT / 'media'
MEDIA.mkdir(exist_ok=True)
DB_URL = os.getenv('DATABASE_URL', f"sqlite:///{BASE/'el_kalel.db'}")
engine = create_engine(DB_URL, connect_args={'check_same_thread': False} if DB_URL.startswith('sqlite') else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')

def password_for_bcrypt(value):
    # bcrypt only accepts passwords up to 72 bytes. Keep existing hashes compatible
    # while preventing startup/login failure when an environment password is longer.
    return value.encode('utf-8')[:72].decode('utf-8', 'ignore')

SECRET = os.getenv('JWT_SECRET', '') or 'ELKALEL-CHANGE-ME-IN-PRODUCTION-' + secrets.token_hex(16)
ALGO='HS256'

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'; id:Mapped[int]=mapped_column(primary_key=True); username:Mapped[str]=mapped_column(String(80),unique=True,index=True); password_hash:Mapped[str]=mapped_column(String(255)); role:Mapped[str]=mapped_column(String(40),default='viewer'); active:Mapped[bool]=mapped_column(Boolean,default=True); staff_id:Mapped[Optional[int]]=mapped_column(ForeignKey('staff.id'),nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Zone(Base):
    __tablename__='zones'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(120),unique=True,index=True); description:Mapped[str]=mapped_column(Text,default=''); active:Mapped[bool]=mapped_column(Boolean,default=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Customer(Base):
    __tablename__='customers'; id:Mapped[int]=mapped_column(primary_key=True); customer_code:Mapped[str]=mapped_column(String(40),unique=True,index=True); name:Mapped[str]=mapped_column(String(160),index=True); phone:Mapped[str]=mapped_column(String(40),index=True); address:Mapped[str]=mapped_column(String(255)); area:Mapped[str]=mapped_column(String(100),index=True); monthly_fee:Mapped[float]=mapped_column(Float,default=0); balance:Mapped[float]=mapped_column(Float,default=0); payment_due_day:Mapped[int]=mapped_column(Integer,default=1); latitude:Mapped[Optional[float]]=mapped_column(Float,nullable=True); longitude:Mapped[Optional[float]]=mapped_column(Float,nullable=True); whatsapp_opt_in:Mapped[bool]=mapped_column(Boolean,default=False); whatsapp_number:Mapped[str]=mapped_column(String(40),default=''); email:Mapped[str]=mapped_column(String(160),default='',index=True); status:Mapped[str]=mapped_column(String(30),default='active'); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class Staff(Base):
    __tablename__='staff'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(160),index=True); phone:Mapped[str]=mapped_column(String(40)); role:Mapped[str]=mapped_column(String(80)); active:Mapped[bool]=mapped_column(Boolean,default=True)
class Truck(Base):
    __tablename__='trucks'; id:Mapped[int]=mapped_column(primary_key=True); plate_number:Mapped[str]=mapped_column(String(40),unique=True,index=True); name:Mapped[str]=mapped_column(String(120)); capacity:Mapped[float]=mapped_column(Float,default=0); status:Mapped[str]=mapped_column(String(40),default='available'); odometer_km:Mapped[float]=mapped_column(Float,default=0); fuel_liters:Mapped[float]=mapped_column(Float,default=0); next_service_due_km:Mapped[float]=mapped_column(Float,default=0); last_service_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True)
class Assignment(Base):
    __tablename__='assignments'; id:Mapped[int]=mapped_column(primary_key=True); area:Mapped[str]=mapped_column(String(100),index=True); staff_id:Mapped[int]=mapped_column(ForeignKey('staff.id')); truck_id:Mapped[Optional[int]]=mapped_column(ForeignKey('trucks.id'),nullable=True); assignment_date:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),index=True); status:Mapped[str]=mapped_column(String(40),default='assigned'); notes:Mapped[str]=mapped_column(Text,default='')
class Collection(Base):
    __tablename__='collections'; id:Mapped[int]=mapped_column(primary_key=True); customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True); staff_id:Mapped[Optional[int]]=mapped_column(ForeignKey('staff.id'),nullable=True); truck_id:Mapped[Optional[int]]=mapped_column(ForeignKey('trucks.id'),nullable=True); area:Mapped[str]=mapped_column(String(100),index=True); collected_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),index=True); status:Mapped[str]=mapped_column(String(40),default='collected'); quantity:Mapped[float]=mapped_column(Float,default=0); latitude:Mapped[Optional[float]]=mapped_column(Float,nullable=True); longitude:Mapped[Optional[float]]=mapped_column(Float,nullable=True); device_id:Mapped[str]=mapped_column(String(120),default=''); offline_recorded:Mapped[bool]=mapped_column(Boolean,default=False); proof_photo:Mapped[str]=mapped_column(String(255),default=''); notes:Mapped[str]=mapped_column(Text,default='')
class Trip(Base):
    __tablename__='trips'; id:Mapped[int]=mapped_column(primary_key=True); truck_id:Mapped[int]=mapped_column(ForeignKey('trucks.id')); driver_id:Mapped[Optional[int]]=mapped_column(ForeignKey('staff.id'),nullable=True); area:Mapped[str]=mapped_column(String(100),index=True); departed_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),index=True); returned_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True); status:Mapped[str]=mapped_column(String(40),default='in_progress'); destination:Mapped[str]=mapped_column(String(160),default='Landfill'); distance_km:Mapped[float]=mapped_column(Float,default=0); odometer_start:Mapped[float]=mapped_column(Float,default=0); odometer_end:Mapped[Optional[float]]=mapped_column(Float,nullable=True); start_latitude:Mapped[Optional[float]]=mapped_column(Float,nullable=True); start_longitude:Mapped[Optional[float]]=mapped_column(Float,nullable=True); end_latitude:Mapped[Optional[float]]=mapped_column(Float,nullable=True); end_longitude:Mapped[Optional[float]]=mapped_column(Float,nullable=True); notes:Mapped[str]=mapped_column(Text,default='')
class LandfillDelivery(Base):
    __tablename__='landfill_deliveries'; id:Mapped[int]=mapped_column(primary_key=True); trip_id:Mapped[int]=mapped_column(ForeignKey('trips.id'),index=True); delivered_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc)); weight_tons:Mapped[float]=mapped_column(Float,default=0); receipt_no:Mapped[str]=mapped_column(String(80),default=''); notes:Mapped[str]=mapped_column(Text,default='')
class Payment(Base):
    __tablename__='payments'; id:Mapped[int]=mapped_column(primary_key=True); customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True); amount:Mapped[float]=mapped_column(Float); method:Mapped[str]=mapped_column(String(50),default='MTN MoMo'); reference:Mapped[str]=mapped_column(String(100),default=''); receipt_no:Mapped[str]=mapped_column(String(100),default=''); received_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),index=True); received_by:Mapped[Optional[int]]=mapped_column(ForeignKey('staff.id'),nullable=True); notes:Mapped[str]=mapped_column(Text,default='')
class SMSLog(Base):
    __tablename__='sms_logs'; id:Mapped[int]=mapped_column(primary_key=True); phone:Mapped[str]=mapped_column(String(40),index=True); message:Mapped[str]=mapped_column(Text); status:Mapped[str]=mapped_column(String(40),default='queued'); provider_ref:Mapped[str]=mapped_column(String(120),default=''); attempts:Mapped[int]=mapped_column(Integer,default=0); sent_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc))
class SMSTemplate(Base):
    __tablename__='sms_templates'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(120),unique=True); message:Mapped[str]=mapped_column(Text); active:Mapped[bool]=mapped_column(Boolean,default=True)
class EmailLog(Base):
    __tablename__='email_logs'; id:Mapped[int]=mapped_column(primary_key=True); to_email:Mapped[str]=mapped_column(String(160),index=True); subject:Mapped[str]=mapped_column(String(255)); message:Mapped[str]=mapped_column(Text); status:Mapped[str]=mapped_column(String(40),default='queued'); provider_ref:Mapped[str]=mapped_column(String(160),default=''); attempts:Mapped[int]=mapped_column(Integer,default=0); error:Mapped[str]=mapped_column(Text,default=''); sent_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),index=True)
class EmailTemplate(Base):
    __tablename__='email_templates'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(120),unique=True); subject:Mapped[str]=mapped_column(String(255)); message:Mapped[str]=mapped_column(Text); active:Mapped[bool]=mapped_column(Boolean,default=True)
class WhatsAppMessage(Base):
    __tablename__='whatsapp_messages'; id:Mapped[int]=mapped_column(primary_key=True); phone:Mapped[str]=mapped_column(String(40),index=True); wa_id:Mapped[str]=mapped_column(String(80),default=''); direction:Mapped[str]=mapped_column(String(20),default='outbound'); message_type:Mapped[str]=mapped_column(String(40),default='text'); message:Mapped[str]=mapped_column(Text,default=''); template_name:Mapped[str]=mapped_column(String(120),default=''); status:Mapped[str]=mapped_column(String(40),default='queued'); provider_message_id:Mapped[str]=mapped_column(String(160),default=''); error:Mapped[str]=mapped_column(Text,default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),index=True); sent_at:Mapped[Optional[datetime]]=mapped_column(DateTime,nullable=True)
class AuditLog(Base):
    __tablename__='audit_logs'; id:Mapped[int]=mapped_column(primary_key=True); actor:Mapped[str]=mapped_column(String(80)); action:Mapped[str]=mapped_column(String(120)); entity:Mapped[str]=mapped_column(String(80)); entity_id:Mapped[str]=mapped_column(String(80),default=''); details:Mapped[str]=mapped_column(Text,default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),index=True)

Base.metadata.create_all(engine)

def ensure_schema_columns():
    # Lightweight compatibility migration for installations upgrading from v3.
    cols = {
        'customers': {
            'whatsapp_opt_in': 'BOOLEAN DEFAULT FALSE',
            'whatsapp_number': "VARCHAR(40) DEFAULT ''",
            'email': "VARCHAR(160) DEFAULT ''",
        }
    }
    with engine.begin() as conn:
        inspector=__import__('sqlalchemy').inspect(conn)
        dialect=engine.dialect.name
        for table, additions in cols.items():
            existing={c['name'] for c in inspector.get_columns(table)}
            for name, typ in additions.items():
                if name in existing: continue
                if dialect == 'postgresql':
                    conn.execute(__import__('sqlalchemy').text(f'ALTER TABLE {table} ADD COLUMN {name} {typ}'))
                elif dialect == 'sqlite':
                    conn.execute(__import__('sqlalchemy').text(f'ALTER TABLE {table} ADD COLUMN {name} {typ}'))
ensure_schema_columns()

def db():
    s=SessionLocal()
    try: yield s
    finally: s.close()
def obj(x): return {c.name:getattr(x,c.name) for c in x.__table__.columns}
def seed():
    s=SessionLocal()
    try:
        if not s.query(User).first(): s.add(User(username='admin',password_hash=pwd.hash(password_for_bcrypt(os.getenv('ADMIN_PASSWORD','ChangeMe123!'))),role='super_admin'))
        if not s.query(Staff).first(): s.add_all([Staff(name='Operations Admin',phone='',role='Administrator'),Staff(name='Collection Team 1',phone='',role='Collector')])
        if not s.query(Truck).first(): s.add(Truck(plate_number='ELK-001',name='EL-KALEL Truck 1',capacity=10,status='available'))
        if not s.query(SMSTemplate).first(): s.add_all([SMSTemplate(name='collection_reminder',message='EL-KALEL ENTERPRISE: Waste collection is scheduled for {date} in {area}. Please bring out your rubbish/dustbin for easy access and collection.'),SMSTemplate(name='payment_reminder',message='EL-KALEL ENTERPRISE: Your waste service payment is due. Customer {code}, balance GHS {balance}. Please make payment to continue uninterrupted service.')])
        if not s.query(EmailTemplate).first(): s.add_all([EmailTemplate(name='collection_reminder',subject='Waste collection reminder — EL-KALEL ENTERPRISE',message='Dear {name},\n\nYour waste collection is scheduled for {date} in {area}. Please make your waste available for easy access and collection.\n\nThank you,\nEL-KALEL ENTERPRISE'),EmailTemplate(name='payment_reminder',subject='Waste service payment reminder — EL-KALEL ENTERPRISE',message='Dear {name},\n\nYour waste service payment is due. Customer {code}. Current balance: GHS {balance}.\n\nPlease make payment to continue uninterrupted service.\n\nThank you,\nEL-KALEL ENTERPRISE')])
        if not s.query(WhatsAppMessage).first(): pass
        s.commit()
    finally: s.close()
seed()

bearer=HTTPBearer(auto_error=False)
ROLE_PERMS={
 'super_admin':{'*'},'admin':{'manage_customers','manage_staff','manage_trucks','manage_assignments','finance','operations','reports','sms','email'},'manager':{'manage_customers','manage_assignments','operations','reports','sms','email'},'finance':{'finance','reports','sms','email'},'dispatcher':{'operations','manage_assignments','reports'},'collector':{'operations'},'driver':{'operations'},'viewer':{'reports'}
}
def token_for(u): return jwt.encode({'sub':str(u.id),'role':u.role,'exp':datetime.now(timezone.utc)+timedelta(hours=12)},SECRET,algorithm=ALGO)
def auth(creds:HTTPAuthorizationCredentials=Depends(bearer),s:Session=Depends(db)):
    if not creds: raise HTTPException(401,'Authentication required')
    try: data=jwt.decode(creds.credentials,SECRET,algorithms=[ALGO]); uid=int(data['sub'])
    except (JWTError,ValueError): raise HTTPException(401,'Invalid token')
    u=s.get(User,uid)
    if not u or not u.active: raise HTTPException(401,'User inactive')
    return u
def require_perm(permission):
    def dep(u=Depends(auth)):
        if '*' not in ROLE_PERMS.get(u.role,set()) and permission not in ROLE_PERMS.get(u.role,set()): raise HTTPException(403,'Insufficient permissions')
        return u
    return dep
def audit(s,u,action,entity,eid='',details=''): s.add(AuditLog(actor=u.username,action=action,entity=entity,entity_id=str(eid),details=details))
def next_code(s): return f"ELK-{(s.query(Customer).count()+1):05d}"

class Login(BaseModel): username:str; password:str
class UserIn(BaseModel): username:str; password:str; role:str='viewer'; staff_id:int|None=None; active:bool=True
class CustomerIn(BaseModel): name:str; phone:str; address:str=''; area:str; monthly_fee:float=Field(ge=0); payment_due_day:int=Field(default=1,ge=1,le=31); latitude:float|None=None; longitude:float|None=None; whatsapp_opt_in:bool=False; whatsapp_number:str=''; email:str=''
class CustomerUpdate(CustomerIn): status:str='active'
class PaymentIn(BaseModel): customer_id:int; amount:float=Field(gt=0); method:str='MTN MoMo'; reference:str=''; receipt_no:str=''; notes:str=''
class CollectionIn(BaseModel): customer_id:int; area:str; staff_id:int|None=None; truck_id:int|None=None; status:str='collected'; quantity:float=Field(default=0,ge=0); latitude:float|None=None; longitude:float|None=None; device_id:str=''; offline_recorded:bool=False; notes:str=''
class CollectionSyncIn(BaseModel): records:list[CollectionIn]
class StaffIn(BaseModel): name:str; phone:str=''; role:str; active:bool=True
class TruckIn(BaseModel): plate_number:str; name:str; capacity:float=Field(default=0,ge=0); status:str='available'; odometer_km:float=Field(default=0,ge=0); fuel_liters:float=Field(default=0,ge=0); next_service_due_km:float=Field(default=0,ge=0)
class TripIn(BaseModel): truck_id:int; driver_id:int|None=None; area:str; destination:str='Landfill'; distance_km:float=Field(default=0,ge=0); odometer_start:float=Field(default=0,ge=0); start_latitude:float|None=None; start_longitude:float|None=None; notes:str=''
class TripReturnIn(BaseModel): odometer_end:float|None=None; end_latitude:float|None=None; end_longitude:float|None=None
class DeliveryIn(BaseModel): trip_id:int; weight_tons:float=Field(gt=0); receipt_no:str=''; notes:str=''
class AssignmentIn(BaseModel): area:str; staff_id:int; truck_id:int|None=None; assignment_date:datetime|None=None; notes:str=''
class ZoneIn(BaseModel): name:str; description:str=''; active:bool=True
class SMSIn(BaseModel): phone:str; message:str
class TemplateIn(BaseModel): name:str; message:str; active:bool=True
class EmailIn(BaseModel): to_email:str; subject:str; message:str
class EmailTemplateIn(BaseModel): name:str; subject:str; message:str; active:bool=True
class WhatsAppTextIn(BaseModel): phone:str; message:str
class WhatsAppTemplateIn(BaseModel): phone:str; template_name:str; language_code:str='en_US'; components:list[dict]=[]

app=FastAPI(title='EL-KALEL Waste Management Operations System',version='4.0.0')
CORS_ORIGINS=[x.strip() for x in os.getenv('CORS_ORIGINS','*').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=CORS_ORIGINS,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

@app.get('/api/health')
def health(s:Session=Depends(db)):
    try: s.execute(__import__('sqlalchemy').text('SELECT 1'))
    except Exception as e: raise HTTPException(503,f'Database unavailable: {e}')
    return {'status':'ok','version':'4.0.0','timestamp':datetime.now(timezone.utc).isoformat()}
@app.post('/api/login')
def login(x:Login,s:Session=Depends(db)):
    u=s.query(User).filter(User.username==x.username).first()
    if not u or not u.active or not pwd.verify(password_for_bcrypt(x.password),u.password_hash): raise HTTPException(401,'Invalid username or password')
    return {'token':token_for(u),'user':{'id':u.id,'username':u.username,'role':u.role,'staff_id':u.staff_id}}
@app.get('/api/me')
def me(u=Depends(auth)): return {'id':u.id,'username':u.username,'role':u.role,'staff_id':u.staff_id}
@app.get('/api/dashboard')
def dashboard(u=Depends(auth),s:Session=Depends(db)):
    start=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0); now=datetime.now(timezone.utc); week=now-timedelta(days=7)
    coll_q=s.query(Collection).filter(Collection.collected_at>=start)
    pay_q=s.query(Payment).filter(Payment.received_at>=start)
    outstanding=float(s.query(func.coalesce(func.sum(Customer.balance),0)).filter(Customer.status=='active').scalar() or 0)
    by_area=s.query(Collection.area,func.count(Collection.id)).filter(Collection.collected_at>=start).group_by(Collection.area).order_by(func.count(Collection.id).desc()).all()
    return {'today':{'collections':coll_q.count(),'payments':float(func_sum:=s.query(func.coalesce(func.sum(Payment.amount),0)).filter(Payment.received_at>=start).scalar() or 0),'missed':s.query(Collection).filter(Collection.collected_at>=start,Collection.status=='missed').count(),'trips':s.query(Trip).filter(Trip.departed_at>=start).count()},'outstanding_balance':outstanding,'active_customers':s.query(Customer).filter(Customer.status=='active').count(),'active_trucks':s.query(Truck).filter(Truck.status!='out_of_service').count(),'in_transit':s.query(Trip).filter(Trip.status=='in_progress').count(),'last_7_days':{'collections':s.query(Collection).filter(Collection.collected_at>=week).count(),'payments':float(s.query(func.coalesce(func.sum(Payment.amount),0)).filter(Payment.received_at>=week).scalar() or 0),'landfill_tons':float(s.query(func.coalesce(func.sum(LandfillDelivery.weight_tons),0)).filter(LandfillDelivery.delivered_at>=week).scalar() or 0)},'collections_by_area':[{'area':a or 'Unassigned','count':c} for a,c in by_area]}

@app.get('/api/users')
def users(u=Depends(require_perm('manage_staff')),s:Session=Depends(db)): return [obj(x) for x in s.query(User).order_by(User.username).all()]
@app.post('/api/users')
def add_user(x:UserIn,u=Depends(require_perm('manage_staff')),s:Session=Depends(db)):
    if s.query(User).filter(User.username==x.username).first(): raise HTTPException(409,'Username already exists')
    z=User(username=x.username,password_hash=pwd.hash(password_for_bcrypt(x.password)),role=x.role,staff_id=x.staff_id,active=x.active); s.add(z); s.flush(); audit(s,u,'CREATE','user',z.id,z.username); s.commit(); return obj(z)

@app.get('/api/zones')
def zones(u=Depends(auth),s:Session=Depends(db)): return [obj(x) for x in s.query(Zone).order_by(Zone.name).all()]
@app.post('/api/zones')
def add_zone(x:ZoneIn,u=Depends(require_perm('manage_assignments')),s:Session=Depends(db)):
    z=Zone(**x.model_dump()); s.add(z); s.flush(); audit(s,u,'CREATE','zone',z.id,z.name); s.commit(); return obj(z)

@app.get('/api/customers')
def customers(q:str='',area:str='',status:str='',limit:int=500,u=Depends(auth),s:Session=Depends(db)):
    query=s.query(Customer)
    if q: query=query.filter(or_(Customer.name.ilike(f'%{q}%'),Customer.phone.ilike(f'%{q}%'),Customer.customer_code.ilike(f'%{q}%')))
    if area: query=query.filter(Customer.area.ilike(f'%{area}%'))
    if status: query=query.filter(Customer.status==status)
    return [obj(x) for x in query.order_by(Customer.name).limit(min(limit,1000)).all()]
@app.post('/api/customers')
def add_customer(x:CustomerIn,u=Depends(require_perm('manage_customers')),s:Session=Depends(db)):
    phone=''.join(ch for ch in x.phone if ch.isdigit() or ch=='+').strip()
    if phone and s.query(Customer).filter(Customer.phone==phone).first():
        raise HTTPException(409,'A customer with this phone number already exists. Search for the existing customer instead of creating a duplicate.')
    c=Customer(customer_code=next_code(s),**{**x.model_dump(),'phone':phone}); c.balance=x.monthly_fee; s.add(c); s.flush(); audit(s,u,'CREATE','customer',c.id,c.customer_code); s.commit(); return obj(c)
@app.put('/api/customers/{cid}')
def update_customer(cid:int,x:CustomerUpdate,u=Depends(require_perm('manage_customers')),s:Session=Depends(db)):
    c=s.get(Customer,cid)
    if not c: raise HTTPException(404,'Customer not found')
    phone=''.join(ch for ch in x.phone if ch.isdigit() or ch=='+').strip()
    duplicate=s.query(Customer).filter(Customer.phone==phone,Customer.id!=cid).first() if phone else None
    if duplicate:
        raise HTTPException(409,'Another customer already uses this phone number.')
    data=x.model_dump()
    data['phone']=phone
    for k,v in data.items(): setattr(c,k,v)
    audit(s,u,'UPDATE','customer',cid,c.customer_code); s.commit(); return obj(c)
@app.delete('/api/customers/{cid}')
def delete_customer(cid:int,u=Depends(require_perm('manage_customers')),s:Session=Depends(db)):
    c=s.get(Customer,cid)
    if not c: raise HTTPException(404,'Customer not found')
    payments=s.query(Payment).filter(Payment.customer_id==cid).count()
    collections=s.query(Collection).filter(Collection.customer_id==cid).count()
    if payments or collections:
        raise HTTPException(409,'This customer has payment or collection records and cannot be deleted. Deactivate the customer instead.')
    code=c.customer_code
    s.delete(c); audit(s,u,'DELETE','customer',cid,code); s.commit(); return {'ok':True,'customer_code':code}
@app.get('/api/customers/{cid}/statement')
def customer_statement(cid:int,u=Depends(auth),s:Session=Depends(db)):
    c=s.get(Customer,cid)
    if not c: raise HTTPException(404,'Customer not found')
    payments=s.query(Payment).filter(Payment.customer_id==cid).order_by(Payment.received_at.desc()).all(); collections=s.query(Collection).filter(Collection.customer_id==cid).order_by(Collection.collected_at.desc()).limit(100).all()
    return {'customer':obj(c),'payments':[obj(x) for x in payments],'collections':[obj(x) for x in collections]}

@app.get('/api/staff')
def staff(u=Depends(auth),s:Session=Depends(db)): return [obj(x) for x in s.query(Staff).order_by(Staff.name).all()]
@app.post('/api/staff')
def add_staff(x:StaffIn,u=Depends(require_perm('manage_staff')),s:Session=Depends(db)):
    z=Staff(**x.model_dump()); s.add(z); s.flush(); audit(s,u,'CREATE','staff',z.id,z.name); s.commit(); return obj(z)
@app.get('/api/trucks')
def trucks(u=Depends(auth),s:Session=Depends(db)): return [obj(x) for x in s.query(Truck).order_by(Truck.plate_number).all()]
@app.post('/api/trucks')
def add_truck(x:TruckIn,u=Depends(require_perm('manage_trucks')),s:Session=Depends(db)):
    z=Truck(**x.model_dump()); s.add(z); s.flush(); audit(s,u,'CREATE','truck',z.id,z.plate_number); s.commit(); return obj(z)

@app.get('/api/collections')
def collections(area:str='',status:str='',limit:int=500,u=Depends(auth),s:Session=Depends(db)):
    q=s.query(Collection)
    if area:q=q.filter(Collection.area.ilike(f'%{area}%'))
    if status:q=q.filter(Collection.status==status)
    return [obj(x) for x in q.order_by(Collection.collected_at.desc()).limit(min(limit,1000)).all()]
def _save_collection(x,u,s):
    if not s.get(Customer,x.customer_id): raise HTTPException(404,'Customer not found')
    z=Collection(**x.model_dump()); s.add(z); s.flush(); audit(s,u,'CREATE','collection',z.id,f'{z.status} / {z.area} / offline={z.offline_recorded}'); s.commit(); return z
@app.post('/api/collections')
def add_collection(x:CollectionIn,u=Depends(require_perm('operations')),s:Session=Depends(db)): return obj(_save_collection(x,u,s))
@app.post('/api/collections/sync')
def sync_collections(x:CollectionSyncIn,u=Depends(require_perm('operations')),s:Session=Depends(db)):
    saved=[]
    for r in x.records: saved.append(obj(_save_collection(r,u,s)))
    return {'saved':len(saved),'records':saved}
@app.post('/api/collections/{cid}/proof')
async def collection_proof(cid:int,file:UploadFile=File(...),u=Depends(require_perm('operations')),s:Session=Depends(db)):
    c=s.get(Collection,cid)
    if not c: raise HTTPException(404,'Collection not found')
    ext=Path(file.filename or '').suffix.lower()[:10] or '.jpg'
    name=f'collection_{cid}_{uuid.uuid4().hex}{ext}'; path=MEDIA/name; data=await file.read()
    if len(data)>5*1024*1024: raise HTTPException(413,'Proof photo exceeds 5 MB')
    path.write_bytes(data); c.proof_photo=name; audit(s,u,'UPLOAD','collection',cid,name); s.commit(); return {'proof_photo':name}

@app.get('/api/payments')
def payments(limit:int=500,u=Depends(auth),s:Session=Depends(db)): return [obj(x) for x in s.query(Payment).order_by(Payment.received_at.desc()).limit(min(limit,1000)).all()]
@app.post('/api/payments')
def add_payment(x:PaymentIn,u=Depends(require_perm('finance')),s:Session=Depends(db)):
    c=s.get(Customer,x.customer_id)
    if not c: raise HTTPException(404,'Customer not found')
    p=Payment(**x.model_dump(),received_by=u.staff_id); c.balance=max(0,c.balance-x.amount); s.add(p); s.flush(); audit(s,u,'CREATE','payment',p.id,f'GHS {x.amount:.2f} for {c.customer_code}'); s.commit(); return {'payment':obj(p),'customer_balance':c.balance}

@app.get('/api/trips')
def trips(u=Depends(auth),s:Session=Depends(db)): return [obj(x) for x in s.query(Trip).order_by(Trip.departed_at.desc()).limit(500).all()]
@app.post('/api/trips')
def add_trip(x:TripIn,u=Depends(require_perm('operations')),s:Session=Depends(db)):
    t=s.get(Truck,x.truck_id)
    if not t: raise HTTPException(404,'Truck not found')
    if t.status=='out_of_service': raise HTTPException(409,'Truck is out of service')
    if t.status=='on_trip': raise HTTPException(409,'Truck is already on a trip')
    t.status='on_trip'; z=Trip(**x.model_dump()); s.add(z); s.flush(); audit(s,u,'CREATE','trip',z.id,f'{t.plate_number} / {z.area}'); s.commit(); return obj(z)
@app.post('/api/trips/{trip_id}/return')
def return_trip(trip_id:int,x:TripReturnIn=TripReturnIn(),u=Depends(require_perm('operations')),s:Session=Depends(db)):
    t=s.get(Trip,trip_id)
    if not t: raise HTTPException(404,'Trip not found')
    if t.status!='in_progress': raise HTTPException(409,'Trip already closed')
    t.status='returned'; t.returned_at=datetime.now(timezone.utc); t.odometer_end=x.odometer_end; t.end_latitude=x.end_latitude; t.end_longitude=x.end_longitude
    truck=s.get(Truck,t.truck_id)
    if truck:
        truck.status='available';
        if x.odometer_end is not None: truck.odometer_km=x.odometer_end
        elif t.distance_km: truck.odometer_km=truck.odometer_km+t.distance_km
    audit(s,u,'UPDATE','trip',trip_id,'Returned'); s.commit(); return obj(t)

@app.get('/api/landfill-deliveries')
def deliveries(u=Depends(auth),s:Session=Depends(db)): return [obj(x) for x in s.query(LandfillDelivery).order_by(LandfillDelivery.delivered_at.desc()).limit(500).all()]
@app.post('/api/landfill-deliveries')
def add_delivery(x:DeliveryIn,u=Depends(require_perm('operations')),s:Session=Depends(db)):
    if not s.get(Trip,x.trip_id): raise HTTPException(404,'Trip not found')
    z=LandfillDelivery(**x.model_dump()); s.add(z); s.flush(); audit(s,u,'CREATE','landfill_delivery',z.id,f'{x.weight_tons} tons'); s.commit(); return obj(z)

@app.get('/api/assignments')
def assignments(u=Depends(auth),s:Session=Depends(db)): return [obj(x) for x in s.query(Assignment).order_by(Assignment.assignment_date.desc()).limit(500).all()]
@app.post('/api/assignments')
def add_assignment(x:AssignmentIn,u=Depends(require_perm('manage_assignments')),s:Session=Depends(db)):
    if not s.get(Staff,x.staff_id): raise HTTPException(404,'Staff not found')
    if x.truck_id and not s.get(Truck,x.truck_id): raise HTTPException(404,'Truck not found')
    z=Assignment(area=x.area,staff_id=x.staff_id,truck_id=x.truck_id,assignment_date=x.assignment_date or datetime.now(timezone.utc),notes=x.notes); s.add(z); s.flush(); audit(s,u,'CREATE','assignment',z.id,x.area); s.commit(); return obj(z)

@app.post('/api/sms')
def queue_sms(x:SMSIn,u=Depends(require_perm('sms')),s:Session=Depends(db)):
    z=SMSLog(phone=x.phone,message=x.message,status='queued'); s.add(z); s.flush(); audit(s,u,'CREATE','sms',z.id,x.phone); s.commit(); return {'id':z.id,'status':z.status}
@app.get('/api/sms')
def sms_logs(u=Depends(auth),s:Session=Depends(db)): return [obj(x) for x in s.query(SMSLog).order_by(SMSLog.created_at.desc()).limit(500).all()]
@app.get('/api/sms/templates')
def sms_templates(u=Depends(auth),s:Session=Depends(db)): return [obj(x) for x in s.query(SMSTemplate).order_by(SMSTemplate.name).all()]
@app.post('/api/sms/templates')
def add_template(x:TemplateIn,u=Depends(require_perm('sms')),s:Session=Depends(db)):
    z=SMSTemplate(**x.model_dump()); s.add(z); s.flush(); audit(s,u,'CREATE','sms_template',z.id,z.name); s.commit(); return obj(z)

def provider_send(phone,message):
    url=os.getenv('SMS_PROVIDER_URL','').strip(); key=os.getenv('SMS_API_KEY','').strip(); sender=os.getenv('SMS_SENDER','EL-KALEL').strip()
    if not url: return False,'SMS_PROVIDER_URL is not configured'
    payload=json.dumps({'to':phone,'message':message,'sender':sender}).encode(); req=urllib.request.Request(url,data=payload,headers={'Content-Type':'application/json','Authorization':f'Bearer {key}' if key else ''},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=15) as r: return 200<=r.status<300, r.read().decode()[:500]
    except Exception as e: return False,str(e)[:500]
@app.post('/api/sms/dispatch')
def dispatch_sms(limit:int=50,u=Depends(require_perm('sms')),s:Session=Depends(db)):
    rows=s.query(SMSLog).filter(SMSLog.status=='queued').order_by(SMSLog.created_at).limit(min(limit,200)).all(); sent=0; failed=0
    for z in rows:
        ok,ref=provider_send(z.phone,z.message); z.attempts+=1
        if ok: z.status='sent'; z.provider_ref=ref; z.sent_at=datetime.now(timezone.utc); sent+=1
        else: z.status='failed' if z.attempts>=3 else 'queued'; z.provider_ref=ref; failed+=1
    audit(s,u,'DISPATCH','sms','',f'sent={sent},failed={failed}'); s.commit(); return {'sent':sent,'failed':failed,'queued_remaining':s.query(SMSLog).filter(SMSLog.status=='queued').count()}


@app.post('/api/sms/reminders/collection')
def collection_reminder(area:str,u=Depends(require_perm('sms')),s:Session=Depends(db)):
    template=s.query(SMSTemplate).filter(SMSTemplate.name=='collection_reminder',SMSTemplate.active==True).first()
    if not template: raise HTTPException(404,'Collection SMS template not found')
    customers=s.query(Customer).filter(Customer.status=='active',Customer.area.ilike(area)).all()
    today=datetime.now(timezone.utc).strftime('%d %B %Y'); queued=0
    for c in customers:
        msg=template.message.format(date=today,area=c.area,code=c.customer_code,balance=f'{c.balance:.2f}')
        s.add(SMSLog(phone=c.phone,message=msg,status='queued')); queued+=1
    audit(s,u,'QUEUE_BULK','sms','',f'collection reminders: {area}, {queued}')
    s.commit(); return {'queued':queued}
@app.post('/api/sms/reminders/payments')
def payment_reminders(u=Depends(require_perm('sms')),s:Session=Depends(db)):
    template=s.query(SMSTemplate).filter(SMSTemplate.name=='payment_reminder',SMSTemplate.active==True).first()
    if not template: raise HTTPException(404,'Payment SMS template not found')
    customers=s.query(Customer).filter(Customer.status=='active',Customer.balance>0).all(); queued=0
    for c in customers:
        msg=template.message.format(date=datetime.now(timezone.utc).strftime('%d %B %Y'),area=c.area,code=c.customer_code,balance=f'{c.balance:.2f}')
        s.add(SMSLog(phone=c.phone,message=msg,status='queued')); queued+=1
    audit(s,u,'QUEUE_BULK','sms','',f'payment reminders: {queued}')
    s.commit(); return {'queued':queued}



def wa_configured():
    return bool(os.getenv('WHATSAPP_ACCESS_TOKEN','').strip() and os.getenv('WHATSAPP_PHONE_NUMBER_ID','').strip())

def email_configured():
    return bool(os.getenv('SMTP_HOST','') and os.getenv('SMTP_FROM',''))

def send_email_now(log, s):
    host=os.getenv('SMTP_HOST',''); port=int(os.getenv('SMTP_PORT','587')); username=os.getenv('SMTP_USERNAME',''); password=os.getenv('SMTP_PASSWORD',''); from_email=os.getenv('SMTP_FROM',''); use_ssl=os.getenv('SMTP_USE_SSL','false').lower()=='true'
    if not host or not from_email: raise RuntimeError('Email is not configured. Set SMTP_HOST and SMTP_FROM.')
    msg=EmailMessage(); msg['From']=from_email; msg['To']=log.to_email; msg['Subject']=log.subject; msg.set_content(log.message)
    if use_ssl:
        with smtplib.SMTP_SSL(host,port,context=ssl.create_default_context(),timeout=30) as server:
            if username: server.login(username,password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host,port,timeout=30) as server:
            server.ehlo(); server.starttls(context=ssl.create_default_context()); server.ehlo()
            if username: server.login(username,password)
            server.send_message(msg)
    log.status='sent'; log.sent_at=datetime.now(timezone.utc); log.provider_ref='smtp'

def dispatch_email_log(log,s):
    log.attempts=(log.attempts or 0)+1
    try: send_email_now(log,s)
    except Exception as e: log.status='failed'; log.error=str(e)
    s.commit(); return log

def normalize_wa_phone(phone:str)->str:
    p=''.join(ch for ch in phone if ch.isdigit())
    if p.startswith('00'): p=p[2:]
    if p.startswith('0'): p='233'+p[1:]
    return p

def whatsapp_api(payload:dict):
    token=os.getenv('WHATSAPP_ACCESS_TOKEN','').strip(); phone_id=os.getenv('WHATSAPP_PHONE_NUMBER_ID','').strip()
    if not token or not phone_id: return False,'WhatsApp Cloud API is not configured',''
    url=f'https://graph.facebook.com/{os.getenv("WHATSAPP_GRAPH_VERSION","v23.0")}/{phone_id}/messages'
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            data=json.loads(r.read().decode()); ids=data.get('messages') or []; return True,'',ids[0].get('id','') if ids else ''
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors='ignore'); return False,body[:1000],''
    except Exception as e: return False,str(e),' '

def send_wa_text(s,phone,message,u=None):
    phone=normalize_wa_phone(phone)
    row=WhatsAppMessage(phone=phone,wa_id=phone,direction='outbound',message_type='text',message=message,status='queued')
    s.add(row); s.flush()
    ok,err,mid=whatsapp_api({'messaging_product':'whatsapp','to':phone,'type':'text','text':{'preview_url':False,'body':message}})
    row.status='sent' if ok else 'failed'; row.error=err; row.provider_message_id=mid; row.sent_at=datetime.now(timezone.utc) if ok else None
    if u: audit(s,u,'SEND','whatsapp',row.id,f'{phone} status={row.status}')
    s.commit(); return row

def whatsapp_customer_reply(s, phone, text):
    c=s.query(Customer).filter(or_(Customer.whatsapp_number==phone,Customer.phone==phone,Customer.phone.like('%'+phone[-9:]))).first()
    command=text.strip().upper()
    if command in ('HI','HELLO','MENU','START'):
        return 'EL-KALEL ENTERPRISE WhatsApp Service\n\nReply with:\n1 - Balance\n2 - Collection status\n3 - Payment information\n4 - Speak to EL-KALEL support'
    if not c:
        return 'Welcome to EL-KALEL ENTERPRISE. We could not match this WhatsApp number to a customer record. Please contact our office to register or update your number.'
    if command in ('1','BALANCE'):
        return f'Customer: {c.name}\nCustomer ID: {c.customer_code}\nOutstanding balance: GHS {c.balance:.2f}'
    if command in ('2','COLLECTION','COLLECTION STATUS'):
        latest=s.query(Collection).filter(Collection.customer_id==c.id).order_by(Collection.collected_at.desc()).first()
        if not latest: return 'No collection record is available yet for your account.'
        return f'Latest collection: {latest.status.replace("_"," ").title()}\nDate: {latest.collected_at.date().isoformat()}\nArea: {latest.area}'
    if command in ('3','PAY','PAYMENT','PAYMENT INFORMATION'):
        return 'Payment options: MTN MoMo, cash or bank. Please use your EL-KALEL customer ID as the payment reference and send your transaction reference to EL-KALEL.'
    if command in ('4','SUPPORT','AGENT'):
        return 'Your request has been received. An EL-KALEL team member will follow up with you.'
    return 'Sorry, I did not understand that. Reply MENU to see the available EL-KALEL WhatsApp options.'

@app.get('/api/email')
def email_logs(u=Depends(require_perm('email')),s:Session=Depends(db)):
    return [obj(x) for x in s.query(EmailLog).order_by(EmailLog.created_at.desc()).limit(500).all()]

@app.get('/api/email/status')
def email_status(u=Depends(require_perm('email'))):
    return {'configured':email_configured(),'smtp_host':bool(os.getenv('SMTP_HOST','')),'from_email':os.getenv('SMTP_FROM',''),'port':int(os.getenv('SMTP_PORT','587'))}

@app.post('/api/email')
def queue_email(x:EmailIn,u=Depends(require_perm('email')),s:Session=Depends(db)):
    if '@' not in x.to_email: raise HTTPException(422,'Valid email address required')
    log=EmailLog(**x.model_dump()); s.add(log); s.flush(); audit(s,u,'CREATE','email',log.id,log.to_email)
    if email_configured(): dispatch_email_log(log,s)
    else: log.status='queued'; s.commit()
    return obj(log)

@app.post('/api/email/templates')
def add_email_template(x:EmailTemplateIn,u=Depends(require_perm('email')),s:Session=Depends(db)):
    if s.query(EmailTemplate).filter(EmailTemplate.name==x.name).first(): raise HTTPException(409,'Template already exists')
    z=EmailTemplate(**x.model_dump()); s.add(z); s.flush(); audit(s,u,'CREATE','email_template',z.id,z.name); s.commit(); return obj(z)

@app.get('/api/email/templates')
def email_templates(u=Depends(require_perm('email')),s:Session=Depends(db)):
    return [obj(x) for x in s.query(EmailTemplate).order_by(EmailTemplate.name).all()]

@app.post('/api/email/dispatch')
def dispatch_emails(u=Depends(require_perm('email')),s:Session=Depends(db)):
    if not email_configured(): raise HTTPException(503,'Email is not configured. Set SMTP_HOST and SMTP_FROM.')
    rows=s.query(EmailLog).filter(EmailLog.status=='queued').order_by(EmailLog.created_at).limit(100).all(); sent=failed=0
    for log in rows:
        dispatch_email_log(log,s)
        if log.status=='sent': sent+=1
        else: failed+=1
    return {'sent':sent,'failed':failed,'processed':len(rows)}

@app.post('/api/email/reminders/payments')
def queue_email_payment_reminders(u=Depends(require_perm('email')),s:Session=Depends(db)):
    tpl=s.query(EmailTemplate).filter(EmailTemplate.name=='payment_reminder',EmailTemplate.active==True).first()
    if not tpl: raise HTTPException(404,'Payment reminder email template not found')
    customers=s.query(Customer).filter(Customer.status=='active',Customer.email!='',Customer.balance>0).all(); queued=0
    for c in customers:
        log=EmailLog(to_email=c.email,subject=tpl.subject.format(name=c.name,code=c.customer_code,balance=f'{c.balance:.2f}'),message=tpl.message.format(name=c.name,code=c.customer_code,balance=f'{c.balance:.2f}'))
        s.add(log); queued+=1
    s.commit(); return {'queued':queued}

@app.post('/api/email/reminders/collection')
def queue_email_collection_reminders(u=Depends(require_perm('email')),s:Session=Depends(db)):
    tpl=s.query(EmailTemplate).filter(EmailTemplate.name=='collection_reminder',EmailTemplate.active==True).first()
    if not tpl: raise HTTPException(404,'Collection reminder email template not found')
    customers=s.query(Customer).filter(Customer.status=='active',Customer.email!='').all(); queued=0
    for c in customers:
        log=EmailLog(to_email=c.email,subject=tpl.subject.format(name=c.name,code=c.customer_code,balance=f'{c.balance:.2f}',date=date.today().isoformat(),area=c.area),message=tpl.message.format(name=c.name,code=c.customer_code,balance=f'{c.balance:.2f}',date=date.today().isoformat(),area=c.area))
        s.add(log); queued+=1
    s.commit(); return {'queued':queued}

@app.get('/api/whatsapp')
def whatsapp_verify(mode:str|None=Query(None,alias='hub.mode'), challenge:str|None=Query(None,alias='hub.challenge'), verify_token:str|None=Query(None,alias='hub.verify_token')):
    expected=os.getenv('WHATSAPP_VERIFY_TOKEN','').strip()
    if mode=='subscribe' and verify_token and expected and hmac.compare_digest(verify_token,expected):
        return int(challenge or '0')
    raise HTTPException(403,'WhatsApp verification failed')

@app.post('/api/whatsapp/webhook')
async def whatsapp_webhook(request:Request, s:Session=Depends(db)):
    raw=await request.body()
    app_secret=os.getenv('WHATSAPP_APP_SECRET','').strip()
    if app_secret:
        supplied=request.headers.get('x-hub-signature-256','')
        expected='sha256='+hmac.new(app_secret.encode(),raw,hashlib.sha256).hexdigest()
        if not supplied or not hmac.compare_digest(supplied,expected):
            raise HTTPException(403,'Invalid WhatsApp webhook signature')
    try:
        payload=json.loads(raw.decode('utf-8'))
        for entry in payload.get('entry',[]):
            for change in entry.get('changes',[]):
                value=change.get('value',{})
                for msg in value.get('messages',[]):
                    wa_id=msg.get('from',''); mtype=msg.get('type','text'); text=(msg.get('text') or {}).get('body','') if mtype=='text' else ''
                    phone=normalize_wa_phone(wa_id)
                    inbound=WhatsAppMessage(phone=phone,wa_id=wa_id,direction='inbound',message_type=mtype,message=text,status='received',provider_message_id=msg.get('id',''))
                    s.add(inbound); s.commit()
                    if text:
                        reply=whatsapp_customer_reply(s,phone,text)
                        send_wa_text(s,phone,reply,None)
        return {'status':'ok'}
    except HTTPException: raise
    except Exception as e:
        s.rollback(); raise HTTPException(500,f'Webhook processing failed: {e}')

@app.get('/api/whatsapp/messages')
def whatsapp_messages(u=Depends(auth),s:Session=Depends(db)):
    return [obj(x) for x in s.query(WhatsAppMessage).order_by(WhatsAppMessage.created_at.desc()).limit(500).all()]

@app.post('/api/whatsapp/send')
def whatsapp_send(x:WhatsAppTextIn,u=Depends(require_perm('sms')),s:Session=Depends(db)):
    if not wa_configured(): raise HTTPException(503,'WhatsApp Cloud API is not configured')
    return obj(send_wa_text(s,x.phone,x.message,u))

@app.post('/api/whatsapp/template')
def whatsapp_template(x:WhatsAppTemplateIn,u=Depends(require_perm('sms')),s:Session=Depends(db)):
    if not wa_configured(): raise HTTPException(503,'WhatsApp Cloud API is not configured')
    phone=normalize_wa_phone(x.phone)
    row=WhatsAppMessage(phone=phone,wa_id=phone,direction='outbound',message_type='template',message='',template_name=x.template_name,status='queued'); s.add(row); s.flush()
    payload={'messaging_product':'whatsapp','to':phone,'type':'template','template':{'name':x.template_name,'language':{'code':x.language_code},'components':x.components}}
    ok,err,mid=whatsapp_api(payload); row.status='sent' if ok else 'failed'; row.error=err; row.provider_message_id=mid; row.sent_at=datetime.now(timezone.utc) if ok else None
    audit(s,u,'SEND','whatsapp',row.id,f'template={x.template_name} status={row.status}'); s.commit(); return obj(row)

@app.get('/api/whatsapp/status')
def whatsapp_status(u=Depends(auth)):
    return {'configured':wa_configured(),'phone_number_id':bool(os.getenv('WHATSAPP_PHONE_NUMBER_ID','')),'verify_token':bool(os.getenv('WHATSAPP_VERIFY_TOKEN','')),'webhook_url':'/api/whatsapp/webhook','graph_version':os.getenv('WHATSAPP_GRAPH_VERSION','v23.0')}

@app.get('/api/audit')
def audit_logs(u=Depends(require_perm('reports')),s:Session=Depends(db)): return [obj(x) for x in s.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(1000).all()]
@app.get('/api/reports/summary')
def report_summary(u=Depends(require_perm('reports')),s:Session=Depends(db),days:int=30):
    days=max(1,min(days,365)); start=datetime.now(timezone.utc)-timedelta(days=days)
    return {'period_days':days,'collections':s.query(Collection).filter(Collection.collected_at>=start).count(),'missed_collections':s.query(Collection).filter(Collection.collected_at>=start,Collection.status=='missed').count(),'payments':float(s.query(func.coalesce(func.sum(Payment.amount),0)).filter(Payment.received_at>=start).scalar() or 0),'landfill_tons':float(s.query(func.coalesce(func.sum(LandfillDelivery.weight_tons),0)).filter(LandfillDelivery.delivered_at>=start).scalar() or 0),'trips':s.query(Trip).filter(Trip.departed_at>=start).count(),'new_customers':s.query(Customer).filter(Customer.created_at>=start).count(),'outstanding_balance':float(s.query(func.coalesce(func.sum(Customer.balance),0)).filter(Customer.status=='active').scalar() or 0)}

def csv_response(rows,filename):
    if not rows: return StreamingResponse(io.StringIO('No data\n'),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename={filename}'})
    out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=list(rows[0].keys())); writer.writeheader(); writer.writerows(rows); out.seek(0)
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename={filename}'})
@app.get('/api/export/{kind}')
def export_data(kind:str,u=Depends(require_perm('reports')),s:Session=Depends(db)):
    models={'customers':Customer,'payments':Payment,'collections':Collection,'trips':Trip,'deliveries':LandfillDelivery,'audit':AuditLog}
    if kind not in models: raise HTTPException(404,'Unknown export')
    rows=[obj(x) for x in s.query(models[kind]).order_by(models[kind].id.desc()).limit(10000).all()]
    return csv_response(rows,f'el_kalel_{kind}.csv')

@app.get('/media/{name}')
def media(name:str):
    p=(MEDIA/name).resolve()
    if MEDIA not in p.parents or not p.exists(): raise HTTPException(404,'File not found')
    return FileResponse(p)
@app.get('/')
def home(): return FileResponse(FRONT/'index.html')
app.mount('/static',StaticFiles(directory=FRONT),name='static')
