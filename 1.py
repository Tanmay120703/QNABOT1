import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from models import db, User, Upload
from forms import LoginForm, SignupForm
from langchain_helper import extract_text, create_faiss_index, get_qa_chain
import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


app = Flask(__name__)
app.secret_key = "b2f8923f2e584937a7fd5b6bcbdcf1046e354a3b03c51f1e"


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))



app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)


@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip().lower()).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
        else:
            hashed_pw = generate_password_hash(form.password.data)
            new_user = User(
                username=username,
                password_hash=hashed_pw,
                dob=form.dob.data,
                gender=form.gender.data
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful. Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    uploads = Upload.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', uploads=uploads)

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('dashboard'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('dashboard'))

    # Save file to disk
    uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'files')
    os.makedirs(uploads_dir, exist_ok=True)
    filename = secure_filename(file.filename)
    file_path = os.path.join(uploads_dir, filename)
    file.save(file_path)


    text_content = extract_text(file_path)


    upload = Upload(user_id=current_user.id, filename=filename, content=text_content)
    db.session.add(upload)
    db.session.commit()


    faiss_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'faiss', str(upload.id))
    os.makedirs(faiss_dir, exist_ok=True)
    create_faiss_index(text_content, faiss_dir)

    flash(" File uploaded and FAISS index created!", "success")
    return redirect(url_for("dashboard"))

@app.route("/qa/<int:upload_id>", methods=["GET", "POST"])
def qa(upload_id):
    upload = Upload.query.get_or_404(upload_id)

    answer = None
    if request.method == "POST":
        question = request.form.get("question")
        try:
            faiss_dir = os.path.join("uploads", "faiss", str(upload.id))
            qa_chain = get_qa_chain(faiss_dir)
            result = qa_chain.invoke({"query": question})   
            answer = result["result"]
        except Exception as e:
            print("[QA ERROR]", e)
            answer = "❌ Error processing the question. Please try again."

    return render_template("qa.html", upload=upload, answer=answer)


@app.context_processor
def utility_processor():
    def get_icon_class(filename):
        ext = filename.split('.')[-1].lower()
        return {
            'pdf': 'fa-solid fa-file-pdf text-danger',
            'docx': 'fa-solid fa-file-word text-primary',
            'doc': 'fa-solid fa-file-word text-primary',
            'txt': 'fa-solid fa-file-lines text-light',
            'csv': 'fa-solid fa-file-csv text-warning'
        }.get(ext, 'fa-solid fa-file text-white')
    return dict(get_icon_class=get_icon_class)

@app.route('/initdb')
def initdb():
    db.create_all()
    return " Database tables created!"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
