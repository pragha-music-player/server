#!/usr/bin/env python3
import argparse
from praghaserver import db, User, Session, Track, Artist, Album
from tabulate import tabulate
from flask import Flask

import config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

def check_args(a):
    if not a.username:
        print("Username parameter is required for this operation.")
        return 1

    if a.username:
        if len(a.username) > 32 or len(a.username) < 4:
            print("Username must be between 4 and 32 characters long")
            return 1

    if a.password:
        if len(a.password) < 8:
            print("Password must at least 8 characters long")
            return 1

    return 0


def add_user(a):
    if not a.password or a.password == '':
        a.password = getpass("Password: ")

    ret_val = check_args(a)
    if ret_val != 0:
        return ret_val

    user = User(a.username, a.password)

    # Commit changes
    db.session.add(user)
    try:
        db.session.commit()
    except User.IntegrityError as e:
        print("Error: {}".format(e.message))
        return 1

    print("User {} succesfully added!".format(a.username))
    return 0


def list_users(a):
    userlist = []
    for user in User.query.all():
        row = {
            'id': user.id,
            'username': user.username,
            'password': user.password,
        }
        userlist.append(row)
    headers = {
        'id': 'ID',
        'username': 'Username',
        'password': 'Password',
    }
    print(tabulate(userlist, headers, tablefmt="grid"))

    return 0


def drop_session(a):
    db.session.query(Session).delete()
    db.session.commit()
    db.session.close()


def show_stats(a):
    stats = [
        ['Tracks', Track.query.count()],
        ['Artists', Artist.query.count()],
        ['Albums', Album.query.count()]
    ]
    print("\nStatistics")
    print(tabulate(stats, tablefmt="grid"))

    sessionlist = []
    for session in Session.query.all():
        row = {
            'id': session.id,
            'token': session.token,
            'expire': session.expire,
        }
        sessionlist.append(row)
    headers = {
        'id': 'ID',
        'token': 'Token',
        'expire': 'Expiration',
    }
    print('\nActive sessionns')
    print(tabulate(sessionlist, headers, tablefmt="grid"))

    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Manage users for PraghaServer')
    parser.add_argument('operation', nargs='+', choices=['add', 'list', 'stats', 'clean-session'], help='Operation')
    parser.add_argument('--username', type=str, help='Username')
    parser.add_argument('--password', type=str, nargs='?', help='Password', default='')
    args = parser.parse_args()

    db.init_app(app)
    with app.app_context():
        op = {
            'add': add_user,
            'list': list_users,
            'stats': show_stats,
            'clean-session': drop_session
        }[args.operation[0]]

        exit(op(args))
