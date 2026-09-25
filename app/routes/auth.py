from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Data wajib diisi', 'danger')
        else:
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('pencarian.home'))
            
            flash('Username atau password salah', 'danger')

    return render_template('auth/login.html', is_register=False)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nama = request.form.get('nama', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not nama or not username or not password:
            flash('Data wajib diisi', 'danger')
        elif len(password) < 8:
            flash('Password minimal 8 karakter', 'danger')
        elif password != confirm:
            flash('Konfirmasi password tidak sesuai', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username telah digunakan', 'danger')
        else:
            user = User(
                nama=nama,
                username=username,
                password=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            
            # Auto login after register as per test scenario 8
            login_user(user)
            return redirect(url_for('pencarian.home'))

    return render_template('auth/login.html', is_register=True)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('auth.login'))
