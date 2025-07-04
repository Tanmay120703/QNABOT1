from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Upload
from langchain_helper import extract_text, get_qa_chain
from forms import LoginForm, SignupForm
import os
from dotenv import load_dotenv
load_dotenv()


# 🔐 Fix for old postgres:// URLs from Render
if os.getenv('DATABASE_URL', '').startswith('postgres://'):
    os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://', 1)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')  # Use environment variable in production
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
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
            session['user_id'] = user.id
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
            flash('Username already exists. Please choose a different one.', 'danger')
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
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    uploads = Upload.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', uploads=uploads)

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    file = request.files['file']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    file_ext = filename.split('.')[-1]
    with open(filepath, "rb") as f:
        content = extract_text(f, file_ext)
    new_upload = Upload(user_id=session['user_id'], filename=filename, content=content)
    db.session.add(new_upload)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/qa/<int:upload_id>', methods=['GET', 'POST'])
def qa(upload_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    upload = Upload.query.get_or_404(upload_id)
    answer = sources = None

    if request.method == 'POST':
        question = request.form['question']
        qa_chain = get_qa_chain(upload.content)
        result = qa_chain(question)
        answer = result['result']

        # Extract page numbers
        source_docs = result.get('source_documents', [])
        page_numbers = []
        for doc in source_docs:
            metadata = getattr(doc, 'metadata', {})
            page = metadata.get('page')
            if page is not None:
                page_numbers.append(str(page))
        if not page_numbers:
            page_numbers = ['1']
        sources = f"page no: {', '.join(sorted(set(page_numbers), key=int))}"

    return render_template('qa.html', upload=upload, answer=answer, sources=sources)

@app.context_processor
def utility_processor():
    def get_icon_class(filename):
        ext = filename.split('.')[-1].lower()
        return {
            'pdf': 'fa-solid fa-file-pdf text-danger',
            'docx': 'fa-solid fa-file-word text-primary',
            'doc': 'fa-solid fa-file-word text-primary',
            'txt': 'fa-solid fa-file-lines text-light',
        }.get(ext, 'fa-solid fa-file text-white')
    return dict(get_icon_class=get_icon_class)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # For quick testing — in production, consider Flask-Migrate
    app.run(debug=True)
