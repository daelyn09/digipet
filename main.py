from flask import Flask, render_template, redirect, request,session,url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import math

app=Flask(__name__)
with open ("config.json","r") as c: 
    param=json.load(c)["parameters"]
app.config["SQLALCHEMY_DATABASE_URI"]=param["local_uri"]
app.config["SECRET_KEY"]=param["secret_key"]
adminuser="lyn09"
adminpassword="12345"

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
    image=db.Column(db.String(300))
    content1=db.Column(db.String(500))
    content2=db.Column(db.String(500))
    slug=db.Column(db.String(200),unique=True)


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/reminders")
def reminders():
    return render_template("reminders.html",param=param)

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
        if user==adminuser and password==adminpassword:
            session["loggedin"]=True
            return redirect(url_for("dashboard"))
    return render_template("login.html",param=param)

@app.route("/signup")
def signup():
    return render_template("signup.html",param=param)

@app.route("/contact", methods=["GET","POST"])
def contact():
    if request.method=="POST":
        Firstname=request.form["first_name"]
        Lastname=request.form["last_name"]
        Email=request.form["email"]
        Message=request.form["message"]
        Date=datetime.today()
        newrow=Contact(first_name=Firstname, last_name=Lastname,email=Email,message=Message,date=Date)
        db.session.add(newrow)
        db.session.commit()
    return render_template("contact.html", param=param)

@app.route("/admin")
def dashboard():
    if "loggedin" in session: #when admin had logged in to the dashboard, all users' blogs and contacts will appear
        blog=Blog.query.all()
        contact=Contact.query.all()
        return render_template("admin/admin.html",blog=blog,contact=contact)
    else:
        return redirect(url_for("login")) #if user tries to log in they will be redirected to login page 

@app.route("/editpost/<string:post_id>", methods=["GET","POST"])
def edit(post_id):
    if request.method=="POST": #see the blog selected
        Title=request.form["title"]
        Subtitle=request.form["subtitle"]
        Author=request.form["author"]
        Image=request.form["image"]
        Location=request.form["location"]
        Slug=request.form["slug"]
        Date=datetime.now()
        Content1=request.form["content1"]
        Content2=request.form["content2"]
        if post_id=="new": #if admin wants to uplaod a new post
            newpost=Blog(title=Title,subtitle=Subtitle,author=Author,image=Image,location=Location,slug=Slug,date=Date,content1=Content1,content2=Content2)
            db.session.add(newpost)
            db.session.commit()
        else:
            blog=Blog.query.filter_by(post_id=post_id).first() #update the existing blog
            blog.title=Title
            blog.subtitle=Subtitle
            blog.author=Author
            blog.image=Image
            blog.location=Location
            blog.slug=Slug
            blog.date=Date
            blog.content1=Content1
            blog.content2=Content2
            db.session.commit()
        return redirect(url_for("dashboard"))
    blog=Blog.query.filter_by(post_id=post_id).first()
    return render_template("admin/editpost.html",param=param,blog=blog,post_id=post_id)

if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run()