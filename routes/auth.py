from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from routes import auth_bp
from models import db, User, Result
from utils.forms import LoginForm, RegistrationForm, UpdateProfileForm, ChangePasswordForm
from services.auth_service import verify_and_change_password, verify_and_update_profile

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user account."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower()
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate and log in an existing user."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user session."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Render profile page, manage details and password updates."""
    # Pre-populate update profile form
    profile_form = UpdateProfileForm(prefix="profile", username=current_user.username, email=current_user.email)
    password_form = ChangePasswordForm(prefix="password")
    
    # Handle form updates by checking prefix submission
    if request.method == 'POST':
        action = request.form.get('submit_action')
        
        if action == 'update_profile':
            # Instantiate with request details
            profile_form = UpdateProfileForm(prefix="profile", formdata=request.form)
            if profile_form.validate_on_submit():
                success, msg = verify_and_update_profile(
                    current_user,
                    profile_form.username.data,
                    profile_form.email.data
                )
                if success:
                    flash(msg, 'success')
                    return redirect(url_for('auth.profile'))
                else:
                    flash(msg, 'danger')
                    
        elif action == 'change_password':
            password_form = ChangePasswordForm(prefix="password", formdata=request.form)
            if password_form.validate_on_submit():
                success, msg = verify_and_change_password(
                    current_user,
                    password_form.current_password.data,
                    password_form.new_password.data
                )
                if success:
                    flash(msg, 'success')
                    return redirect(url_for('auth.profile'))
                else:
                    flash(msg, 'danger')
                    
    # Retrieve user quiz history
    history = Result.query.filter_by(user_id=current_user.id).order_by(Result.attempted_at.desc()).all()
    
    return render_template(
        'profile.html',
        profile_form=profile_form,
        password_form=password_form,
        history=history
    )
