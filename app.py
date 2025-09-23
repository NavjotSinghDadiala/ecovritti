from flask import Flask, render_template, request, redirect, url_for, session , jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "abc-secret-key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user"] = user.username
            if user.username == "admin":
                return redirect(url_for("admin"))
            return redirect(url_for("user"))
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

@app.route('/test', methods=['POST'])
def test_post():
    data = request.json  # Get JSON data from request
    print(f"Received: {data}")  # Print to console for debugging
    return jsonify({"status": "success", "message": "Data received"}), 200

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin_user = User(username="admin", password="admin")
            db.session.add(admin_user)
            db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)
