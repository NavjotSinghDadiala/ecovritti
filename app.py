from flask import Flask, render_template, request, redirect, url_for, session , jsonify , flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "abc-secret-key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    resident_id = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        resident_id = request.form.get("resident_id", None)
        role = "resident"  # Always resident

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for("register"))

        # Check if username/email already exists (optional safeguard)
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash("Username or Email already exists", "danger")
            return redirect(url_for("register"))

        # Create new user
        user = User(username=username, email=email, password=password,
                    resident_id=resident_id, role=role)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # match username & password in DB
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user"] = user.username
            session["role"] = user.role  # store role in session

            # redirect based on role
            if user.role == "secretary":
                return redirect(url_for("secretary"))
            elif user.username == "admin":  # special admin check
                return redirect(url_for("admin"))
            else:
                return redirect(url_for("user"))  # default for residents
        else:
            return "Invalid credentials"

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

@app.route("/admin")
def admin():
    if "user" not in session or session["user"] != "admin":
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")

@app.route("/user")
def user():
    if "user" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["user"]).first()
    return render_template("user_dashboard.html", user=user)

@app.route("/secretary")
def secretary():
    if "user" not in session or session.get("role") != "secretary":
        return redirect(url_for("login"))
    return render_template("secretary_dashboard.html")

@app.route("/how")
def how():
    return render_template("how.html")

@app.route("/footer")
def footer():
    return render_template("footer.html")



#-------------------------------------------------HARDWARE APIS -------------------------------------------------

@app.route('/test', methods=['POST'])
def test_post():
    data = request.json  # Get JSON data from request
    print(f"Received: {data}")  # Print to console for debugging
    return jsonify({"status": "success", "message": "Data received"}), 200



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin_user = User(username="admin", password="admin" ,email = "dadialanavjotsingh@gmail.com", role="admin")
            db.session.add(admin_user)
            secretary_user = User(username="secretary", password="123" ,email = "dadialanavjotsingh15@gmail.com", role="secretary")
            db.session.add(secretary_user)
            db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)
