from flask import Flask, session, redirect, request
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
engine = create_engine("DATABASE_URL") # Heroku URI 
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

# Homepage
@app.route('/')
def index():
    raise NotImplementedError

# Login Page
@app.route('/login', method=["GET", "POST"])
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
        return "LOGIN PAGE"


# Register Page
@app.route('/register', method=["GET","POST"])
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
        return "REGISTER PAGE"
        

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")




if __name__ == '__main__':
    app.run(debug=True)