import hashlib
import os
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


def username_registration():
    username = input("Enter username: ")
    if type(username) is not str:
        raise TypeError
    for i in username:
        if i not in POSSIBLE_USERNAME_CHARS:
            raise BadCharacterError
    if username[0].isdigit():
        raise StartsWithDigitError
    if is_user_exists(username):
        print("Username already exists.")
        return False
    return username


def password_registration():
    password = input("Enter password: ")
    if type(password) is not str:
        raise TypeError
    if len(password) < MIN_PASSWORD_LENGTH:
        raise MinLengthError
    for i in password:
        if i not in POSSIBLE_PASSWORD_CHARS:
            raise PossibleCharError
    if not any(c.isdigit() for c in password):
        raise NeedCharError
    salt, password_hash = hash_password(password)
    return salt, password_hash


def register_user():
    username = username_registration()  # обработать на фронте неудавшуюся регу
    salt, password_hash = password_registration()
    try:
        with open(DATA_FILE, "a") as f:
            f.write(f"{username},{password_hash},{salt}\n")
        print("User registered successfully.")
        return True
    except Exception as e:
        print(f"Error writing to file: {e}")
        return False


def login_user():
    username = input("Enter username: ")
    password = input("Enter password: ")

    user_data = get_user_data(username)
    if user_data:
        stored_username, stored_hash, stored_salt = user_data
        if verify_password(password, stored_salt, stored_hash):
            print("Login successful.")
            return True
        else:
            print("Incorrect password.")
            return False
    else:
        print("User not found.")
        return False


def is_user_exists(username):
    with open(DATA_FILE, "r") as f:
        for line in f:
            user, _, _ = line.strip().split(",")
            if user == username:
                return True
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
        print ("Data file is corrupted, user data is unavailable")
        return None


def main():
    while True:
        print("\nChoose an option:")
        print("1. Register")
        print("2. Login")
        print("3. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            register_user()
        elif choice == "2":
            login_user()
        elif choice == "3":
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()

