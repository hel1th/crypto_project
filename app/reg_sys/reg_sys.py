import hashlib
import os
import streamlit as st
from dotenv import load_dotenv
from exceptions import *
import string

load_dotenv()

PASSWORD_SALT = os.getenv("PASSWORD_SALT")
DATA_FILE = "users.txt"
POSSIBLE_PASSWORD_CHARS = string.ascii_letters + string.digits + string.punctuation
POSSIBLE_USERNAME_CHARS = string.ascii_letters + string.digits + "'-_."
MIN_PASSWORD_LENGTH = 8

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    salted_password = salt + password + PASSWORD_SALT
    hashed_password = hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
    return salt, hashed_password


def verify_password(password, stored_salt, stored_hash):
    salted_password = stored_salt + password + PASSWORD_SALT
    hashed_password = hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
    return hashed_password == stored_hash


def register_user(username, password):
    try:
        if not isinstance(username, str):
            raise TypeError("Username must be a string.")
        for char in username:
            if char not in POSSIBLE_USERNAME_CHARS:
                raise PossibleCharError(f"Invalid character in username: {char}")
        if username[0].isdigit():
            raise StartsWithDigitError("Username cannot start with a digit.")
        if is_user_exists(username):
            st.error("Username already exists.")
            return False
        
        if not isinstance(password, str):
            raise TypeError("Password must be a string.")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise MinLengthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
        for char in password:
            if char not in POSSIBLE_PASSWORD_CHARS:
                raise PossibleCharError(f"Invalid character in password: {char}")
        if not any(char.isdigit() for char in password):
            raise NeedCharError("Password must contain at least one digit.")

        salt, password_hash = hash_password(password)
        with open(DATA_FILE, "a") as f:
            f.write(f"{username},{password_hash},{salt}\n")
        st.success("User registered successfully!")
        return True

    except TypeError as e:
        st.error(f"Registration Error: {e}")
        return False
    except BadCharacterError as e:
        st.error(f"Registration Error: {e}")
        return False
    except StartsWithDigitError as e:
        st.error(f"Registration Error: {e}")
        return False
    except MinLengthError as e:
        st.error(f"Registration Error: {e}")
        return False
    except PossibleCharError as e:
        st.error(f"Registration Error: {e}")
        return False
    except NeedCharError as e:
        st.error(f"Registration Error: {e}")
        return False
    except Exception as e:
        st.error(f"Registration Error: An unexpected error occurred: {e}")
        return False

def login_user(username, password):
    user_data = get_user_data(username)
    if user_data:
        stored_username, stored_hash, stored_salt = user_data
        if verify_password(password, stored_salt, stored_hash):
            st.success("Login successful.")
            st.session_state.logged_in = True
            st.session_state.username = username
            return True
        else:
            st.error("Incorrect password.")
            return False
    else:
        st.error("User not found.")
        return False


def is_user_exists(username):
    try:
        with open(DATA_FILE, "r") as f:
            for line in f:
                user, _, _ = line.strip().split(",")
                if user == username:
                    return True
    except FileNotFoundError:
        return False
    return False


def get_user_data(username):
    try:
        with open(DATA_FILE, "r") as f:
            for line in f:
                user, password_hash, salt = line.strip().split(",")
                if user == username:
                    return user, password_hash, salt
        return None
    except FileNotFoundError:
        return None
    except ValueError:
        st.error("Data file is corrupted, user data is unavailable")
        return None
    

def authentication_page():
    auth_option = st.radio("Choose an option:", ("Login", "Register"))

    if auth_option == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username and password:
                login_user(username, password)
                if st.session_state.logged_in:
                    st.rerun()
            else:
                st.warning("Please enter both username and password.")

    elif auth_option == "Register":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Register"):
            if username and password:
                register_user(username, password)
            else:
                st.warning("Please enter both username and password.")


def main():
    st.header("Добро пожаловать в мир криптохомячков")
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None

    if st.session_state.logged_in:
        st.write(f"Welcome, {st.session_state.username}!")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
    else:
        authentication_page() 

if __name__ == "__main__":
    main()

