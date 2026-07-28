import re
from models import db, User

def verify_and_change_password(user, current_password, new_password):
    """
    Verifies user's current password and updates it to the new password.
    
    Returns:
        tuple: (success_bool, message_str)
    """
    if not user.check_password(current_password):
        return False, "Incorrect current password."
        
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."
        
    user.set_password(new_password)
    db.session.commit()
    return True, "Password successfully updated."

def verify_and_update_profile(user, username, email):
    """
    Validates and updates username and email for a user, avoiding conflicts.
    
    Returns:
        tuple: (success_bool, message_str)
    """
    username = username.strip()
    email = email.strip().lower()
    
    if not username or not email:
        return False, "Username and Email are required fields."
        
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, "Invalid email address format."
        
    # Check if username is taken by another user
    existing_username = User.query.filter(User.username == username, User.id != user.id).first()
    if existing_username:
        return False, "Username is already taken."
        
    # Check if email is taken by another user
    existing_email = User.query.filter(User.email == email, User.id != user.id).first()
    if existing_email:
        return False, "Email address is already in use."
        
    user.username = username
    user.email = email
    db.session.commit()
    return True, "Profile details successfully updated."
