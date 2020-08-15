import os

from flask import Flask, session, redirect, request, render_template, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configure session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine('postgres://vraflmfjiprudl:35133ceeb18809cfd81c661d26d7ac39ce8c2674eb14e69a4550c9384366630c@ec2-3-208-50-226.compute-1.amazonaws.com:5432/d9fj78f13oje2m') # Heroku URI 
database = scoped_session(sessionmaker(bind=engine))
db = database()

# Login required function
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# Login Page
@app.route('/login', methods=["GET", "POST"])
def login():
    session.clear()

    # POST
    if request.method == "POST":
        # Check if username filled
        if not request.form.get("username"): # Form name username
            return "ERROR" # Error page

        # Check if password filled
        elif not request.form.get("password"): # Form name password
            return "ERROR" # Error page

        rows  = db.execute("SELECT * FROM users WHERE username = :user", \
            {'user':request.form.get('username')}).fetchall()

        if len(rows) != 1:
            return "ERROR" # Error page
        elif not check_password_hash(request.form.get('password'), rows[0]['password']):
            return "ERROR" # Error page
        
        session['user_id'] = rows[0]['id']

        return redirect("/")

    # GET
    else:
        return render_template("login.html")


# Register Page
@app.route('/register', methods=["GET","POST"])
def register():
    session.clear()

    # POST
    if request.method == "POST":
        rows = db.execute("SELECT * FROM users").fetchall()
        
        # Check if username filled
        if not request.form.get("username"): # Form name username
            return "ERROR"
        # Check if password filled
        elif not request.form.get("password"): # Form name password
            return "ERROR"
        # Check if password confirmation filled
        elif not request.form.get("confirm"): # Form name confirm
            return "ERROR"
        # Check Password and Confirmation
        elif request.form.get("password") != request.form.get("confirm"):
            return "ERROR"

        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check username availability
        for row in rows:
            if username == row['username']:
                return "ERROR"
        
        hash_password = generate_password_hash(password)

        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", \
            {'username':username, 'password':hash_password})
        
        user_id = db.execute("SELECT id FROM users WHERE username = :username", \
            {'username':username}).fetchone()
        
        session['user_id'] = user_id

        db.commit()

        return redirect("/")

    # GET
    else:
        return render_template("register.html")
        

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# Homepage:
@app.route('/')
@login_required
def index():
    courses = []

    rows = db.execute("SELECT * FROM courses").fetchall()
    
    for row in rows:
        courses.append([row['id'], row['course_name'], row['description']])

    return render_template("index.html", courses=courses)


# Course Page (Review and Rating of a course)
@app.route("/course/<course_id>", methods=["GET", "POST"])
@login_required
def course(course_id):
    # POST
    if request.method == "POST":
        
        # Check if review filled
        if not request.form.get('review'):
            return "ERROR"
        # Check if rating filled
        elif not request.form.get('rating'):
            return "ERROR"
        
        review = request.form.get('review')
        rating = int(request.form.get('rating'))

        # Check if user have multiple submission
        rows = db.execute("SELECT * FROM reviews WHERE course_id=:course AND user_id=:user", \
            {'course':course_id, 'user':session['user_id'][0]}).fetchall()
        print(rows)
        if len(rows) == 0:
            db.execute("INSERT INTO reviews (course_id,user_id,review,rating) VALUES (:course, :user, :review, :rating)", \
                {'course':course_id, 'user':session['user_id'][0], 'review':review, 'rating':rating})
            db.commit()

            link = "/course/" + course_id
            return redirect(link)
    
        else:
            return "ERROR"

    #GET
    else:
        courses = db.execute("SELECT * FROM courses").fetchall()

        # Query course from course database
        course = db.execute("SELECT * FROM courses WHERE id=:course", \
            {'course':course_id}).fetchall()
        
        if course is None:
            return "ERROR"

        rows = db.execute("SELECT * FROM reviews WHERE course_id=:course", \
            {'course':course_id}).fetchall()
        
        if len(rows) == 0:
            return render_template("course.html", 
                courses=courses, 
                name=course[0]['course_name'],
                web=course[0]['course_web'],
                desc=course[0]['description'],
                check=False)

        else:
            reviews = []

            for row in rows:
                userid = row['user_id']
                username = db.execute("SELECT username FROM users WHERE id=:user", {'user':userid}).fetchone()
                reviews.append([username['username'], row['review'], row['rating']])

            rating = db.execute("SELECT AVG(rating) FROM reviews WHERE course_id=:course", {'course':course_id}).fetchone()

            return render_template("course.html",
                courses=courses,
                name=course[0]['course_name'],
                web=course[0]['course_web'],
                desc=course[0]['description'],
                check=True,
                reviews=reviews,
                rating=round(rating['avg'],2))


# Search Function (Returns Search Results)
@app.route("/search")
@login_required
def search():
    search = request.form.get('search') # Form name search
    search = "%" + search + "%"

    rows = db.execute("SELECT * FROM courses WHERE course_name LIKE :search OR course_web LIKE :search", \
        {'search':search}).fetchall()
    
    results = []

    for row in rows:
        ratings = db.execute("SELECT AVG(rating) FROM reviews WHERE course_id=:course", {'course':row['id']}).fetchone()
        rating = round(float(ratings[0]),2)
        results.append([row['course_name'], row['course_web'], rating])

    return {
        'results':results # LIST: [name, web, rating]
    }

if __name__ == '__main__':
    app.run(debug=True)