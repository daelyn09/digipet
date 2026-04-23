from flask import Flask, render_template, redirect, request,session,url_for,flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import math
from flask_login import LoginManager,login_user,logout_user,login_required,current_user,UserMixin
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
import os #this module is used so that when users has signed up the system will remember their credentials and also more effective than using session
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from password_strength import PasswordPolicy
from password_strength import PasswordStats
from flask_apscheduler import APScheduler
from apscheduler.jobstores.base import JobLookupError
from dotenv import load_dotenv
import re

load_dotenv()

policy=PasswordPolicy.from_names(
    length=8,
    uppercase=1,
    numbers=1, #minimum 2 numbers
)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

app=Flask(__name__)
app.config['MAIL_SERVER']='smtp.gmail.com' #the SMTP server address used to send emails (this means im using gmail)
app.config['MAIL_PORT']= 465 #port number for the SMTP server. TLS=587, SSL=465
app.config['MAIL_USERNAME']=os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD']=os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS']= False #enables Transport Layer Security encryption. 
app.config['MAIL_USE_SSL']= True #enables SSL encryption from the start of the connection.
app.config['UPLOAD_FOLDER']='static/userpic' #where to save uploaded files
app.config['BLOG_UPLOAD_FOLDER']='static/blogpics' 
mail=Mail(app)
with open ("config.json","r") as c: 
    param=json.load(c)["parameters"]
app.config["SQLALCHEMY_DATABASE_URI"]=param["local_uri"]
app.config["SECRET_KEY"]=param["secret_key"]
scheduler=APScheduler()
scheduler.init_app(app)
scheduler.start()
login_manager=LoginManager()
login_manager.login_view="login"
login_manager.init_app(app)

#email validation
def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

@login_manager.user_loader
def load_user(user_id):
    if user_id=="admin123":
        return AdminUser()
    else:
        return Users.query.get(user_id)

#for the email notification
def send_reminder_email(email_address,first_name,pet_name,title,notes):
    with app.app_context():
        msg=Message(f"Reminder for {pet_name}:{title}",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[email_address])
        msg.body=f"Hi {first_name}! This is a reminder for {pet_name}😊.\n\nTask: {title}!📋\nNotes: {notes}"
        mail.send(msg)
        print(f"Email sent to {email_address} at {datetime.now()}")

def reload_jobs():
    with app.app_context():
        now=datetime.now()
        future_reminders=Reminder.query.all()
        for rem in future_reminders:
            run_at = datetime.strptime(f"{rem.date} {rem.time}", '%Y-%m-%d %H:%M:%S')
            if run_at>now:
                pet=Pet.query.get(rem.pet_id)
                user=Users.query.filter_by(username=rem.username).first()
                if user is None or pet is None: 
                    continue
                scheduler.add_job(
                    id=f"reminder_{rem.list_id}",
                    func=send_reminder_email,
                    trigger='date',
                    run_date=run_at,
                    args=[user.email,user.first_name,pet.name,rem.title,rem.notes]
                )

db=SQLAlchemy(app)
class Contact(db.Model):
    sno=db.Column(db.Integer,primary_key=True)
    first_name=db.Column(db.String(100),nullable=False)
    last_name=db.Column(db.String(100),nullable=False)
    email=db.Column(db.String(100),nullable=False)
    message=db.Column(db.String(5000),nullable=False)
    date=db.Column(db.String(100))

class Blog(db.Model):
    post_id=db.Column(db.Integer, primary_key=True)
    title=db.Column(db.String(100))
    subtitle=db.Column(db.String(200))
    location=db.Column(db.String(50))
    author=db.Column(db.String(30))
    date=db.Column(db.Date)
    image=db.Column(db.String(300), nullable=True)
    content1=db.Column(db.String(500))
    content2=db.Column(db.String(500))
    slug=db.Column(db.String(200),unique=True)

class Users(UserMixin, db.Model):
    id=db.Column(db.Integer, primary_key=True)
    first_name=db.Column(db.String(200), nullable=False)
    last_name=db.Column(db.String(200), nullable=False)
    username=db.Column(db.String(250), nullable=False)
    email=db.Column(db.String(200), nullable=False)
    password=db.Column(db.String(200), nullable=False)
    profile_pic=db.Column(db.String(300),nullable=True)

class Reminder(db.Model):
    list_id=db.Column(db.Integer, primary_key=True)
    pet_id=db.Column(db.Integer, db.ForeignKey("pet.pet_id"), nullable=True) #added a pet id for each pet
    username=db.Column(db.String(100))
    title=db.Column(db.String(100))
    date=db.Column(db.String(100))
    time=db.Column(db.String(100))
    notes=db.Column(db.String(100))
    is_archived=db.Column(db.Boolean, default=False) #added this for archive

class Pet(db.Model):
    pet_id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(200), nullable=False)
    name=db.Column(db.String(200), nullable=False)
    image=db.Column(db.String(500), nullable=True)

class AdminUser(UserMixin):
    def __init__(self):
        self.id="admin123"
        self.username="lyn09"
        self.first_name="Daelyn"
        self.is_Admin=True
        self.email="francinesalim@gmail.com"
        self.profile_pic="https://i.pinimg.com/736x/46/af/b0/46afb0dfc7d37d8c3b82d143611c5299.jpg"

@app.route("/")
def home():
    blog=Blog.query.order_by(Blog.date.desc()).limit(10).all()
    return render_template("index.html",blog=blog)

def generate_slug(title, post_id):
    slug=title.lower()
    slug=re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = slug.strip('-')[:30]
    return f"{slug}-{post_id}"

@app.route("/blogs")
def blogs():
    postrow=Blog.query.order_by(Blog.date.desc()).all()
    n=2 #number of posts per page
    total_posts=len(postrow)
    last=math.ceil(total_posts/n)
    page=request.args.get("page",1,type=int)

    if page < 1: page = 1
    if page > last and last > 0: page = last
    
    start = (page-1)*n
    end = start + n
    slice = postrow[start:end]

    prev= url_for('blogs', page=page-1) if page > 1 else "#"
    next= url_for('blogs',page=page+1) if page < last else "#"

    return render_template("blogs.html",param=param,slice=slice,prev=prev,next=next,Users=Users)

@app.route("/blogdetail/<slug>", methods=["GET"])
def blogdetail(slug):
    singlepost=Blog.query.filter_by(slug=slug).first()
    return render_template("blogdetail.html",param=param, singlepost=singlepost,Users=Users)

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        user=request.form["username"]
        password=request.form["password"]
        userrow=Users.query.filter_by(username=user).first()
        if userrow and userrow.password==password:
            login_user(userrow)
            return redirect(url_for("dashboard"))
        elif user==param["adminusername"] and password==param["adminpassword"]:
            adminobj=AdminUser()
            login_user(adminobj)
            print(current_user.first_name)
            return redirect(url_for("dashboard"))
        else: 
            flash("Please check your login details and try again")
            return redirect(url_for("login"))
    return render_template("login.html",param=param)

@app.route("/signup",methods=["GET","POST"])
def signup():
    if request.method=="POST":
        First_name=request.form["first_name"]
        Last_name=request.form["last_name"]
        Username=request.form["username"]
        Email=request.form["email"]
        Password=request.form["password"]
        Confirmpassword=request.form["confirmpassword"]
        checkpolicy=policy.test(Password)
        check=Users.query.filter_by(email=Email).first() #when a user typed in existing email address it will give a flash msg
        checkusername=Users.query.filter_by(username=Username).first() #when a user typed in existing username it will also give a flash msg
        if not is_valid_email(Email):
            flash("Please enter a valid email address","email_invalid")
            return redirect(url_for("signup"))
        elif check: 
            flash("Email address has already existed","email_error")
            return redirect(url_for("signup"))
        elif checkusername: 
            flash("Username has already existed","username_dupe")
            return redirect(url_for("signup"))
        elif checkpolicy:
            flash("Password not strong enough. Must include uppercase, numbers, and 8+ characters.","pass_not_strong")
            return redirect(url_for("signup"))
        elif Password != Confirmpassword:
            flash("Passwords don't match","password_error")
            return redirect(url_for("signup"))
        newuser=Users(first_name=First_name,last_name=Last_name,username=Username,email=Email,password=Password)
        db.session.add(newuser)
        db.session.commit()
        login_user(newuser)
        return redirect(url_for("dashboard"))
    return render_template("signup.html",param=param)

@app.route("/logout")
@login_required
def logout():
    logout_user() #user can logout using this function
    return redirect(url_for("login"))

@app.route("/contact", methods=["GET","POST"])
def contact():
    if request.method=="POST":
        Firstname=request.form["first_name"]
        Lastname=request.form["last_name"]
        Email=request.form["email"]
        message=request.form["message"]
        email=Message(Firstname,sender=Email,recipients=["francinesalim@gmail.com"])
        email.body=message+"\n"+Email
        mail.send(email)
        Date=datetime.today()
        newrow=Contact(first_name=Firstname, last_name=Lastname,email=Email,message=Message,date=Date)
        db.session.add(newrow)
        db.session.commit()
    return render_template("contact.html", param=param)

@app.route("/admin")
@login_required
def dashboard():
    style=""
    if current_user.first_name=="Daelyn": #admin login
        credentials=Users.query.all()
        blog=Blog.query.all()
    else: #user login
        user=current_user.username
        blog=Blog.query.filter_by(author=user).all()
        credentials=Users.query.filter_by(username=user).all()
        style="display:none;"
    return render_template("admin/admin.html",blog=blog,credentials=credentials,style=style,param=param)

@app.route("/edituser/<int:id>",methods=["GET","POST"])
@login_required
def edituser(id):
    if current_user.first_name != "Daelyn":
        flash("Access denied.")
        return redirect(url_for("dashboard"))
    user=Users.query.get_or_404(id)
    if request.method=="POST":
        Firstname=request.form["first_name"]
        Lastname=request.form["last_name"]
        Username=request.form["username"]
        Email=request.form["email"]
        user.first_name=Firstname
        user.last_name=Lastname
        user.username=Username
        user.email=Email
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("admin/edituser.html",param=param,user=user)

@app.route("/deleteuser/<int:id>")
@login_required
def deleteuser(id):
    if current_user.first_name !="Daelyn":
        flash("Access denied.")
        return redirect(url_for("dashboard"))
    user=Users.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/editprofile",methods=["GET","POST"])
@login_required
def editprofile():
    if request.method=="POST":
        file=request.files.get("profile_pic")
        if file and file.filename != "":
            upload_result=cloudinary.uploader.upload(file)
            current_user.profile_pic=upload_result["secure_url"]
            db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("admin/editprofile.html",param=param,user=current_user)

@app.route("/editpost/<string:post_id>", methods=["GET","POST"])
def edit(post_id):
    blog=None
    image_url=None
    if post_id != "new":
        blog=Blog.query.filter_by(post_id=post_id).first()
        if blog:
            image_url=blog.image #keep existing image

    if request.method=="POST": #see the blog selected
        Title=request.form["title"]
        Subtitle=request.form["subtitle"]
        Author=current_user.username
        Location=request.form["location"]
        Content1=request.form["content1"]
        Content2=request.form["content2"]
        Date=datetime.now()
        
        file_to_upload=request.files.get('image')
        #added this
        if file_to_upload and file_to_upload.filename !='': #checks if user uploaded a new image. if yes, it sends the file to cloudinary, if no, image_url stays as the old one.
            upload_result = cloudinary.uploader.upload(file_to_upload)
            image_url = upload_result["secure_url"]
        if image_url is None:
            image_url=""

        if post_id=="new": #if admin wants to uplaod a new post
            newpost=Blog(title=Title,subtitle=Subtitle,author=current_user.username,
                         image=image_url,location=Location,slug="temp",
                         date=Date,content1=Content1,content2=Content2)
            db.session.add(newpost)
            db.session.commit()
            newpost.slug=generate_slug(Title,newpost.post_id)
            db.session.commit()
        else:
            if blog:
                blog.title=Title
                blog.subtitle=Subtitle
                blog.author=Author
                blog.image=image_url
                blog.location=Location
                blog.slug=generate_slug(Title, blog.post_id)
                blog.date=Date
                blog.content1=Content1
                blog.content2=Content2
        db.session.commit()
        return redirect(url_for("dashboard"))
    img=image_url if image_url and image_url != "" else url_for("static",filename="default.jpg")
    return render_template("admin/editpost.html",param=param,blog=blog,post_id=post_id,img=img)

@app.route("/delete/<string:post_id>",methods=["GET","POST"])
def delete(post_id):
    post=Blog.query.filter_by(post_id=post_id).first()
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/reminder/<string:pet_id>/<string:list_id>",methods=["GET","POST"])
def reminder(pet_id, list_id):
    if request.method=="POST":    
        Username=current_user.username
        Title=request.form["title"]
        Date=request.form["date"]
        Time=request.form["time"]
        Notes=request.form["notes"]
        #added this
        run_at = datetime.strptime(f"{Date} {Time}", '%Y-%m-%d %H:%M')
        pet=Pet.query.get(pet_id)

        if list_id=="new":
            newreminder=Reminder(username=Username, pet_id=pet_id, title=Title,date=Date,time=Time,notes=Notes,is_archived=False)
            db.session.add(newreminder)
            db.session.commit()
            target_id=newreminder.list_id

        #added this
        else:
            existing=Reminder.query.filter_by(list_id=list_id).first()
            if existing:
                existing.title = Title
                existing.date = Date
                existing.time = Time
                existing.notes = Notes
                db.session.commit()
                target_id=list_id

                try:
                    scheduler.remove_job(id=f"reminder_{target_id}")
                except JobLookupError:
                    pass
            
        scheduler.add_job(
            id=f"reminder_{target_id}",
            func=send_reminder_email,
            trigger='date',
            run_date=run_at,
            args=[current_user.email,current_user.first_name,pet.name,Title,Notes]
        )
        return redirect(url_for("reminder",pet_id=pet_id,list_id="new"))
    reminder_to_edit=Reminder.query.filter_by(list_id=list_id).first() if list_id != "new" else None
    allreminders=Reminder.query.filter_by(username=current_user.username,pet_id=pet_id,is_archived=False).all() #gets everyone's reminders  
    now=datetime.now()
    for r in allreminders: 
        r.is_past=(str(r.date)+''+str(r.time)) < now.strftime('%Y-%m-%d %H:%M:%S')
    return render_template("admin/reminders.html",param=param,reminder=reminder_to_edit,list_id=list_id,allreminders=allreminders,pet_id=pet_id,now=datetime.now())

@app.route("/editreminder/<string:pet_id>/<string:list_id>",methods=["GET","POST"])
def editreminder(pet_id, list_id):
        if request.method=="POST":
            Title=request.form["title"]
            Date=request.form["date"]
            Time=request.form["time"][:5]
            Notes=request.form["notes"]
            reminder=Reminder.query.filter_by(list_id=list_id).first()
            reminder.title=Title
            reminder.date=Date
            reminder.time=Time
            reminder.notes=Notes
            reminder.is_archived=False #means it's not archived
            db.session.commit()
            
            #reschedule the job
            run_at=datetime.strptime(f"{Date} {Time}",'%Y-%m-%d %H:%M')
            pet=Pet.query.get(reminder.pet_id)
            user=Users.query.filter_by(username=reminder.username).first()
            
            try:
                scheduler.remove_job(id=f"reminder_{list_id}")
            except JobLookupError:
                pass

            scheduler.add_job(
                id=f"reminder_{list_id}",
                func=send_reminder_email,
                trigger='date',
                run_date=run_at,
                args=[current_user.email, current_user.first_name, pet.name, Title, Notes]
            )
            return redirect(url_for("reminder",pet_id=pet_id,list_id="new"))
        reminder=Reminder.query.filter_by(list_id=list_id).first()
        return render_template("admin/editreminder.html",param=param,reminder=reminder,list_id=list_id, pet_id=pet_id)

@app.route("/reminder/delete/<string:pet_id>/<int:list_id>")
@login_required
def delete_reminder(pet_id, list_id):
    reminder=Reminder.query.filter_by(list_id=list_id).first()
    #added this
    try:
        scheduler.remove_job(id=f"reminder_{list_id}")
    except JobLookupError:
        pass
    db.session.delete(reminder)
    db.session.commit()
    return redirect(url_for("reminder",pet_id=pet_id,list_id=list_id))

@app.route("/petprofile/<string:pet_id>", methods=["GET","POST"])
@login_required
def petprofile(pet_id):
    pet=None
    image_url=None
    if pet_id !="new":
        pet=Pet.query.filter_by(pet_id=pet_id).first()
        if pet:
            image_url=pet.image
    if request.method == "POST":
        Name = request.form.get("name")
        file_to_upload = request.files.get("image")
        if file_to_upload and file_to_upload.filename != '':
            upload_result = cloudinary.uploader.upload(file_to_upload)
            image_url = upload_result["secure_url"]
        if pet_id == "new":
            newpet = Pet(username=current_user.username, name=Name, image=image_url)
            db.session.add(newpet)
            db.session.commit()
            return redirect(url_for("reminder", pet_id=newpet.pet_id,list_id="new"))
        else:
            if pet:
                pet.name = Name
                if image_url:
                    pet.image = image_url
                db.session.commit()
                return redirect(url_for("petprofile",pet_id=pet_id))
    allpets=Pet.query.filter_by(username=current_user.username).all()
    reminders = Reminder.query.filter_by(pet_id=pet_id).all() if pet_id !="new" else []
    img = image_url if image_url else url_for("static", filename="default.jpg")
    return render_template("admin/petprofile.html",param=param,pet=pet,pet_id=pet_id,img=img,reminders=reminders, allpets=allpets)

@app.route("/editpetprofile/<string:pet_id>", methods=["GET","POST"])
def editpetprofile(pet_id):
    pet=None
    image_url=None
    if pet_id != "new":
        pet=Pet.query.filter_by(pet_id=pet_id).first()
        if pet:
            image_url=pet.image

    if request.method=="POST":
        Name=request.form["name"]

        file_to_upload=request.files.get('image')
        #added this
        if file_to_upload and file_to_upload.filename !='': #checks if user uploaded a new image. if yes, it sends the file to cloudinary, if no, image_url stays as the old one.
            upload_result = cloudinary.uploader.upload(file_to_upload)
            image_url = upload_result["secure_url"]
        if image_url is None:
            image_url=""
    
        if pet:
            pet.name=Name
            pet.image=image_url
        db.session.commit()
        return redirect(url_for("petprofile",pet_id=pet_id))
    img=image_url if image_url and image_url != "" else url_for("static",filename="default.jpg")
    return render_template("admin/editpetprofile.html",param=param,pet=pet,pet_id=pet_id,img=img)

@app.route("/deletepet/<string:pet_id>")
@login_required
def deletepet(pet_id):
    Reminder.query.filter_by(pet_id=pet_id).delete()
    pet=Pet.query.filter_by(pet_id=pet_id).first()
    db.session.delete(pet)
    db.session.commit()
    return redirect(url_for("petprofile",pet=pet,pet_id=pet_id))

@app.route("/archive_reminder/<int:list_id>", methods=["GET"])
@login_required
def archive_reminder(list_id):
    #this bypasses SQLAlchemy's caching and sends the SQL command directly to MySQL. this just tells MySQL directly to set is_archived=1 for that specific row. 
    db.session.execute(
        db.text("UPDATE reminder SET is_archived = 1 WHERE list_id = :id"),
        {"id": list_id}
    )
    db.session.commit()
    reminder = db.session.get(Reminder, list_id)
    return redirect(url_for("archive", pet_id=reminder.pet_id))

@app.route("/archive/<string:pet_id>")
@login_required
def archive(pet_id):
    pet=db.session.get(Pet,pet_id)
    archived_reminders=Reminder.query.filter_by(pet_id=pet_id, is_archived=True).all()
    return render_template("admin/archive.html", param=param, pet=pet, allreminders=archived_reminders, pet_id=pet_id)

@app.route("/unarchive_reminder/<int:list_id>")
@login_required
def unarchive_reminder(list_id):
    reminder=db.session.get(Reminder, list_id)
    reminder.is_archived=False
    db.session.commit()
    return redirect(url_for("archive", pet_id=reminder.pet_id))

@app.route("/archive/delete/<string:pet_id>/<int:list_id>")
@login_required
def delete_archived_reminder(pet_id,list_id):
    reminder=Reminder.query.filter_by(list_id=list_id).first()
    #added this
    try:
        scheduler.remove_job(id=f"reminder_{list_id}")
    except JobLookupError:
        pass
    db.session.delete(reminder)
    db.session.commit()
    return redirect(url_for("archive",pet_id=pet_id))

if __name__=="__main__":
    with app.app_context():
        db.create_all()
        reload_jobs()
    app.run()