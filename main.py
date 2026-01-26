from flask import Flask, render_template, redirect, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

app=Flask(__name__)
with open ("config.json","r") as c: 
    param=json.load(c)["parameters"]
app.config["SQLALCHEMY_DATABASE_URI"]=param["local_uri"]
app.config["SECRET_KEY"]=param["secret_key"]

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


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/reminders")
def reminders():
    return render_template("reminders.html",param=param)

@app.route("/blogs", methods=["GET"])
def blogs():
    singlepost=Blog.query.get(1)
    return render_template("blogs.html",param=param,singlepost=singlepost)

@app.route("/settings")
def settings():
    return render_template("settings.html",param=param)

@app.route("/login")
def login():
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

if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run()