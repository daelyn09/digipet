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

cloudinary.config(
    cloud_name="dshz7ewkw",
    api_key="971153553473416",
    api_secret="33rLc2ZzKqH-Vs-7_qJHM9GUfOE",
    secure=True
)

app=Flask(__name__)
app.config['MAIL_SERVER']='smtp.gmail.com' #the SMTP server address used to send emails (this means im using gmail)
app.config['MAIL_PORT']= 465 #port number for the SMTP server. TLS=587, SSL=465
app.config['MAIL_USERNAME']='francinesalim@gmail.com'
app.config['MAIL_PASSWORD']='vdkl lolq yblz xdef'
app.config['MAIL_USE_TLS']= False #enables Transport Layer Security encryption. 
app.config['MAIL_USE_SSL']= True #enables SSL encryption from the start of the connection.
app.config['UPLOAD_FOLDER']='static/userpic' #where to save uploaded files
app.config['BLOG_UPLOAD_FOLDER']='static/blogpics' 
mail=Mail(app)
with open ("config.json","r") as c: 
    param=json.load(c)["parameters"]
app.config["SQLALCHEMY_DATABASE_URI"]=param["local_uri"]
app.config["SECRET_KEY"]=param["secret_key"]
login_manager=LoginManager()
login_manager.login_view="login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    if user_id=="admin123":
        return AdminUser()
    else:
        return Users.query.get(user_id)

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

class Reminder(db.Model):
    list_id=db.Column(db.Integer, primary_key=True)
    pet_id=db.Column(db.Integer, db.ForeignKey("pet.pet_id"), nullable=True)
    username=db.Column(db.String(100))
    title=db.Column(db.String(100))
    date=db.Column(db.String(100))
    time=db.Column(db.String(100))
    notes=db.Column(db.String(100))

class Pet(db.Model):
    pet_id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(200), nullable=False)
    name=db.Column(db.String(200), nullable=False)
    image=db.Column(db.String(500), nullable=True)

class AdminUser(UserMixin):
    def __init__(self):
        self.id="admin123"
        self.username="admin"
        self.first_name="Daelyn"
        self.is_Admin=True

@app.route("/")
def home():
    blog=Blog.query.all()
    return render_template("index.html",blog=blog)

@app.route("/blogs")
def blogs():
    db.session.commit()
    postrow=Blog.query.all()
    n=2 #number of posts per page
    last=math.ceil(len(postrow)/n)
    page=request.args.get("page")
    if (not str(page).isnumeric()): 
        page=1
    page=int(page)
    j=(page-1)*n
    slice=postrow[j:j+n]
    if page==1:
        prev="#"
        next="/?page="+str(page+1)
    elif page==last:
        next="#"
        prev="/?page="+str(page-1)
    else:
        prev="/?page="+str(page-1)
        next="/?page="+str(page+1)
    return render_template("blogs.html",param=param,slice=slice,prev=prev,next=next)

@app.route("/blogdetail/<slug>", methods=["GET"])
def blogdetail(slug):
    singlepost=Blog.query.filter_by(slug=slug).first()
    return render_template("blogdetail.html",param=param, singlepost=singlepost)

@app.route("/settings")
def settings():
    return render_template("settings.html",param=param)

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
        check=Users.query.filter_by(email=Email).first() #when a user typed in existing email address it will give a flash msg
        if check: 
            flash("Email address has already existed","email_error")
            return redirect(url_for("signup"))
        elif Password != Confirmpassword:
            flash("Passwords don't match","password_error")
            return redirect(url_for("signup"))
        newuser=Users(first_name=First_name,last_name=Last_name,username=Username,email=Email,password=Password)
        db.session.add(newuser)
        db.session.commit()
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
        email=Message(Firstname,sender=Email,recipients=["salimdael@gmail.com"])
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
    if current_user.first_name=="admin": #admin login
        credentials=Users.query.all()
        blog=Blog.query.all()
    else: #user login
        user=current_user.first_name
        blog=Blog.query.filter_by(author=user)
        credentials=Users.query.filter_by(first_name=user)
        style="display:none;"
    return render_template("admin/admin.html",blog=blog,credentials=credentials,style=style,param=param)

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
        Author=request.form["author"]
        Location=request.form["location"]
        Slug=request.form["slug"]
        Date=datetime.now()
        Content1=request.form["content1"]
        Content2=request.form["content2"]
        file_to_upload=request.files.get('image')
        if file_to_upload: #checks if user uploaded a new image. if yes, it sends the file to cloudinary, if no, image_url stays as the old one.
            upload_result = cloudinary.uploader.upload(file_to_upload)
            image_url = upload_result["secure_url"]
            print(image_url)
        if post_id=="new": #if admin wants to uplaod a new post
            newpost=Blog(title=Title,subtitle=Subtitle,author=Author,image=image_url,location=Location,slug=Slug,date=Date,content1=Content1,content2=Content2)
            db.session.add(newpost)
        else:
            if blog:
                blog.title=Title
                blog.subtitle=Subtitle
                blog.author=Author
                blog.image=image_url
                blog.location=Location
                blog.slug=Slug
                blog.date=Date
                blog.content1=Content1
                blog.content2=Content2
        db.session.commit()
        return redirect(url_for("dashboard"))
    img=image_url if image_url else url_for("static",filename="default.jpg")
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
        if list_id=="new":
            newreminder=Reminder(username=Username, pet_id=pet_id, title=Title,date=Date,time=Time,notes=Notes)
            db.session.add(newreminder)
            db.session.commit()
            return redirect(url_for("reminder",list_id=newreminder.list_id))
        else:
            existing=Reminder.query.filter_by(list_id=list_id).first()
            if existing:
                existing.title = Title
                existing.date = Date
                existing.time = Time
                existing.notes = Notes
                db.session.commit()
    reminder=Reminder.query.filter_by(list_id=list_id).first() if list_id != "new" else None
    allreminders=Reminder.query.filter_by(username=current_user.username).all() #gets everyone's reminders  
    return render_template("admin/reminders.html",param=param,reminder=reminder,list_id=list_id,allreminders=allreminders,pet_id=pet_id)

@app.route("/editreminder/<string:pet_id>/<string:list_id>",methods=["GET","POST"])
def editreminder(pet_id, list_id):
        if request.method=="POST":
            Title=request.form["title"]
            Date=request.form["date"]
            Time=request.form["time"]
            Notes=request.form["notes"]
            reminder=Reminder.query.filter_by(list_id=list_id).first()
            reminder.title=Title
            reminder.date=Date
            reminder.time=Time
            reminder.notes=Notes
            db.session.commit()
            return redirect(url_for("reminder",pet_id=pet_id,list_id="new"))
        reminder=Reminder.query.filter_by(list_id=list_id).first()
        return render_template("admin/editreminder.html",param=param,reminder=reminder,list_id=list_id, pet_id=pet_id)

@app.route("/reminder/delete/<string:pet_id>/<int:list_id>")
@login_required
def delete_reminder(pet_id, list_id):
    reminder=Reminder.query.filter_by(list_id=list_id).first()
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
            return redirect(url_for("petprofile", pet_id=newpet.pet_id))
        else:
            if pet:
                pet.name = Name
                if image_url:
                    pet.image = image_url
                db.session.commit()

    reminders = Reminder.query.filter_by(pet_id=pet_id).all() if pet_id !="new" else []
    img = image_url if image_url else url_for("static", filename="default.jpg")
    return render_template("admin/petprofile.html",param=param,pet=pet,pet_id=pet_id,img=image_url,reminders=reminders)

if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run()