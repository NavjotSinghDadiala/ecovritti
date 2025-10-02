from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
from os import environ
import requests
import numpy as np
import cv2
#import tensorflow as tf
#from tensorflow import keras
import qrcode
from datetime import datetime



app = Flask(__name__)
app.secret_key = "abc-secret-key"
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,     
    "pool_recycle": 280,      
    "pool_size": 20,           
    "max_overflow": 30,        
    "pool_timeout": 30         
}

# Encode password
password = "Sihhackathon@123"
encoded_password = password.replace("@", "%40")

ESP32_URL = "http://10.243.2.48/capture"

# Configure database
if 'DATABASE_URL' in environ:
    app.config['SQLALCHEMY_DATABASE_URI'] = environ.get('DATABASE_URL').replace('postgres://', 'postgresql://')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://u862294565_sih:{encoded_password}@82.25.121.49/u862294565_sih"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User model
class User(db.Model, UserMixin):
    """Authentication table for admin + secretary only"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)  
    password = db.Column(db.String(120), nullable=False) 
    email = db.Column(db.String(120), unique=True, nullable=True)

class Resident(db.Model, UserMixin):
    """All residents added by secretary, approved by admin"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False)
    room_no = db.Column(db.String(50), nullable=False)
    contact = db.Column(db.String(15), nullable=True)
    society = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(200), nullable=True)  
    points = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="Pending") 
    role = db.Column(db.String(50), nullable=True)      
    qr_code_path = db.Column(db.String(200), nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))



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
        role = "resident" 

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for("register"))

        # Check if username/email already exists (optional safeguard)
        existing_user = Resident.query.filter((Resident.username == username) | (Resident.email == email)).first()
        if existing_user:
            flash("Username or Email already exists", "danger")
            return redirect(url_for("register"))

        # Create new user
        user = Resident(username=username, email=email, password=password,
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

        # First check User table
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            if user.role == "secretary":
                return redirect(url_for("secretary"))
            elif user.role == "admin":
                return redirect(url_for("admin"))
            else:
                flash("Unauthorized role", "danger")
                return redirect(url_for("login"))

        # If not found in User, check Resident table
        resident = Resident.query.filter_by(username=username).first()
        if resident and resident.password == password:
            login_user(resident)
            if resident.role == "resident":
                return redirect(url_for("user"))
            else:
                flash("Unauthorized role", "danger")
                return redirect(url_for("login"))

        # If both checks fail
        flash("Invalid credentials", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")




@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/admin")
@login_required
def admin():
    if current_user.role != "admin":
        return redirect(url_for("login"))

    pending = Resident.query.filter_by(status="Pending").order_by(Resident.id.asc()).all()
    approved = Resident.query.filter_by(status="Approved").order_by(Resident.id.desc()).all()
    return render_template("admin_dashboard.html", pending=pending, approved=approved)


@app.route("/user")
@login_required
def user():
    return render_template("user_dashboard.html", user=current_user)

@app.route("/secretary", methods=["GET", "POST"])
@login_required
def secretary():
    if current_user.role != "secretary":
        return redirect(url_for("login"))

    if request.method == "POST":
        # this POST comes from the form secretary uses to add residents
        username = request.form.get("username")
        room_no = request.form.get("room_no")
        contact = request.form.get("contact")
        society = request.form.get("society")

        if not username or username.strip() == "":
            flash("Username is required.", "danger")
            return redirect(url_for("secretary"))

        new_resident = Resident(
            username=username,
            room_no=room_no,
            contact=contact,
            society=society,
            status="Pending",
            created_by=current_user.id
        )
        db.session.add(new_resident)
        db.session.commit()
        flash("Resident entry added and is pending admin approval.", "success")
        return redirect(url_for("secretary"))

    # show all entries created by this secretary (you can also show all pending in society)
    residents = Resident.query.filter_by(created_by=current_user.id).order_by(Resident.id.desc()).all()
    return render_template("secretary_dashboard.html", residents=residents)

@app.route("/manage_residents", methods=["GET", "POST"])
@login_required
def manage_residents():
    if current_user.role != "secretary":
        return redirect(url_for("login"))

    if request.method == "POST":
        action = request.form.get("action", "add")
        if action == "add":
            username = request.form.get("username")
            room_no = request.form.get("room_no")
            contact = request.form.get("contact")
            society = request.form.get("society")
            if not username or username.strip() == "":
                flash("Username is required.", "danger")
                return redirect(url_for("manage_residents"))
            new_resident = Resident(
                username=username,
                room_no=room_no,
                contact=contact,
                society=society,
                status="Pending",
                created_by=current_user.id
            )
            db.session.add(new_resident)
            db.session.commit()
            flash("Resident added successfully.", "success")
        elif action == "edit":
            resident_id = request.form.get("resident_id")
            resident = Resident.query.filter_by(id=resident_id, created_by=current_user.id).first()
            if resident:
                new_username = request.form.get("username")
                if not new_username or new_username.strip() == "":
                    flash("Username is required.", "danger")
                    return redirect(url_for("manage_residents"))
                resident.username = new_username
                resident.room_no = request.form.get("room_no")
                resident.contact = request.form.get("contact")
                resident.society = request.form.get("society")
                db.session.commit()
                flash("Resident updated successfully.", "success")
            else:
                flash("Resident not found or unauthorized.", "danger")
        elif action == "delete":
            resident_id = request.form.get("resident_id")
            resident = Resident.query.filter_by(id=resident_id, created_by=current_user.id).first()
            if resident:
                db.session.delete(resident)
                db.session.commit()
                flash("Resident deleted successfully.", "success")
            else:
                flash("Resident not found or unauthorized.", "danger")
        return redirect(url_for("manage_residents"))

    residents = Resident.query.filter_by(created_by=current_user.id).order_by(Resident.id.desc()).all()
    return render_template("secretary_dashboard.html", residents=residents)

@app.route("/admin/approve/<int:resident_id>", methods=["POST"])
@login_required
def admin_approve_resident(resident_id):
    if current_user.role != "admin":
        return redirect(url_for("login"))
    resident = Resident.query.get_or_404(resident_id)

    # update status & role
    resident.status = "Approved"
    resident.role = "resident"
    db.session.commit()   # commit early so resident.id etc are stable

    # generate QR and update resident.qr_code_path
    try:
        generate_qr_for_resident(resident)
    except Exception as e:
        # you may want to log; keep the approved status but notify admin
        flash(f"Approved but QR generation failed: {str(e)}", "warning")
        return redirect(url_for("admin"))

    # generate plaintext password for the resident (username + room_no)
    try:
        generate_password_for_resident(resident)
    except Exception as e:
        flash(f"Approved but password generation failed: {str(e)}", "warning")
        return redirect(url_for("admin"))

    flash(f"Resident {resident.username} approved and QR generated.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/reject/<int:resident_id>", methods=["POST"])
@login_required
def admin_reject_resident(resident_id):
    if current_user.role != "admin":
        return redirect(url_for("login"))
    resident = Resident.query.get_or_404(resident_id)
    resident.status = "Rejected"
    db.session.commit()
    flash(f"Resident {resident.username} rejected.", "info")
    return redirect(url_for("admin"))

@app.route("/how")
def how():
    return render_template("how.html")

@app.route("/footer")
def footer():
    return render_template("footer.html")

@app.route("/why")
def why():
    return render_template("why.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")





#-------------------------------------------------HARDWARE APIS -------------------------------------------------

@app.route('/test', methods=['POST'])
def test_post():
    data = request.json  # Get JSON data from request
    print(f"Received: {data}")  # Print to console for debugging
    return jsonify({"status": "success", "message": "Data received"}), 200

# Load the Keras model once at startup
'''MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model', 'model.keras')
model = keras.models.load_model(MODEL_PATH)
CLASS_NAMES = ['organic', 'recyclable']'''

'''def predict_waste(image):
    # Preprocess: resize, convert to RGB, scale to [0,1]
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (224, 224))
    img = img.astype('float32') / 255.0
    img = np.expand_dims(img, axis=0)
    preds = model.predict(img)
    class_idx = int(np.argmax(preds))
    return CLASS_NAMES[class_idx]'''

def generate_qr_for_resident(resident):
    qr_data = f"ResidentID:{resident.id}|Name:{resident.username}|Room:{resident.room_no}|Society:{resident.society}"
    img = qrcode.make(qr_data)
    qr_path = os.path.join('static', 'qrcodes', f'resident_{resident.id}.png')
    img.save(qr_path)
    resident.qr_code_path = qr_path
    db.session.commit()

def generate_password_for_resident(resident):
    """Create plaintext password for resident as name + room_no (no hashing)."""
    name_part = (resident.username or "resident").strip()
    resident.password = f"{name_part}{resident.room_no}"
    db.session.commit()

'''@app.route("/capture", methods=["GET"])
def capture_from_esp():
    """Capture image from ESP32-CAM"""
    try:
        resp = requests.get(ESP32_URL, timeout=10)
        if resp.status_code != 200:
            return jsonify({"error": "Failed to capture"}), 500

        # Convert to NumPy image
        img_array = np.frombuffer(resp.content, np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # Run ML model
        prediction = predict_waste(image)

        # TODO: send GPIO / actuator signal based on prediction
        # if prediction == "plastic":
        #     trigger_sensor("blue_bin")
        # elif prediction == "organic":
        #     trigger_sensor("green_bin")

        return jsonify({"status": "success", "waste_type": prediction})
    except Exception as e:
        return jsonify({"error": str(e)}), 500'''

@app.route("/capture_image")
def capture_image():
    """Return raw image from ESP32-CAM so <img> can display it"""
    try:
        resp = requests.get(ESP32_URL, timeout=10)
        if resp.status_code != 200:
            return "Failed to capture", 500

        return Response(resp.content, mimetype="image/jpeg")
    except Exception as e:
        return f"Error: {str(e)}", 500



if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # create static/qrcodes dir
        os.makedirs(os.path.join(app.static_folder or 'static', 'qrcodes'), exist_ok=True)

        if not User.query.filter_by(username="admin").first():
            admin_user = User(username="admin", email="dadialanavjotsingh@gmail.com", role="admin")
            admin_user.password = "admin"   # change in prod
            db.session.add(admin_user)

        if not User.query.filter_by(username="secretary").first():
            sec_user = User(username="secretary", email="dadialanavjotsingh15@gmail.com", role="secretary")
            sec_user.password = "secretary"  # change in prod
            db.session.add(sec_user)

        db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)
