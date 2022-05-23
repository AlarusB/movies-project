import uuid, os, hashlib, pymysql
from flask import Flask, request, render_template, redirect, url_for, session, abort, flash, jsonify
app = Flask(__name__)

# Register the setup page and import create_connection()
from utils import create_connection, setup
app.register_blueprint(setup)


def login(result):
    session['logged_in'] = True
    session['first_name'] = result['first_name']
    session['email'] = result['email']
    session['role'] = result['role']
    session['id'] = result['id']

@app.before_request
def restrict():
    restricted_pages = [
        'list_users',
        'view_user',
        'edit_user',
        'delete_user'
        ]

    if 'logged_in' not in session and request.endpoint in restricted_pages:
        return redirect(url_for('login'))

    

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/checkemail')
def check_email():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = 'SELECT * FROM users WHERE email = %s'
            values = (
                request.args['email']
            )
            cursor.execute(sql, values)
            result = cursor.fetchone()
            if result:
                return jsonify({ 'status': 'Taken' })
            else:
                return jsonify({ 'status': 'OK' }) 

# TODO: Add a '/register' (add_user) route that uses INSERT
@app.route('/register', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':

        password =  request.form['password']
        encrypted_password = hashlib.sha256(password.encode()).hexdigest()

        avatar_filename = None    

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO users
                    (first_name, last_name, email, password, avatar)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    encrypted_password,
                    avatar_filename
                )
                try:
                    cursor.execute(sql, values)
                    connection.commit()
                except pymysql.err.IntegrityError:
                    flash('Email has already been taken')
                    return redirect(url_for('add_user'))
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = 'SELECT * FROM users WHERE email = %s AND password = %s'
                values = (
                    request.form['email'],
                    encrypted_password
                )
                cursor.execute(sql, values)
                result = cursor.fetchone()
                if result:
                    session['logged_in'] = True
                    session['first_name'] = result['first_name']
                    session['email'] = result['email']
                    session['role'] = result['role']
                    session['id'] = result['id']
                    return redirect(url_for('view_user', id=result['id']))
        return redirect(url_for('home'))
    return render_template('users_add.html')

# Page for adding movies
@app.route('/addmovie', methods=['GET', 'POST'])
def add_movie():
    if request.method == 'POST':

        poster_filename = None    

        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO users
                    (title, genre, year_released, summary, poster_filename)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (
                    request.form['title'],
                    request.form['genre'],
                    request.form['year_released'],
                    request.form['summary'],
                    poster_filename
                )
        return redirect(url_for('home'))
    return render_template('movies_add.html')


# TODO: Add a '/dashboard' (list_users) route that uses SELECT
@app.route('/dashboard')
def list_users():

    if session['role'] != 'admin':
        return abort(404)
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users")
            result = cursor.fetchall()
    return render_template('users_list.html', result=result)

# TODO: Add a '/profile' (view_user) route that uses SELECT
@app.route('/view')
def view_user():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id=%s", request.args['id'])
            result = cursor.fetchone()
    return render_template('users_view.html', result=result)

# TODO: Add a '/delete_user' route that uses DELETE
@app.route('/delete')
def delete_user():

    if session['role'] != 'admin' and str(session['id']) != request.args['id']:
        return abort(404)
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "DELETE FROM users WHERE id = %s"
            values = (
                request.args['id']
            )
            cursor.execute(sql, values)
            connection.commit()
            # Log out if function
        
    if str(session['id']) == request.args['id']:
        return redirect(url_for('logout'))
    else:
        return redirect(url_for('list_users'))
# TODO: Add an '/edit_user' route that uses UPDATE

@app.route('/edit', methods=['GET', 'POST'])
def edit_user():

    if session['role'] != 'admin' or str(session['id']) != request.args['id']:
        return abort(404)
    if request.method == 'POST':

        if request.files['avatar'].filename:
            avatar_image = request.files["avatar"]
            ext = os.path.splitext(avatar_image.filename)[1]
            avatar_filename = str(uuid.uuid4())[:8] + ext
            avatar_image.save("static/images/" + avatar_filename)
            if request.form['old_avatar'] != 'None' and os.path.exists("static/images/" + request.request.form['old_avatar']):
                os.remove("static/images/" + request.form['old_avatar'])
        elif request.form['old_avatar'] != 'None':
            avatar_filename = request.form['old_avatar']
        else:
            avatar_filename = None

        with create_connection() as connection:    

            with connection.cursor() as cursor:
                sql = """UPDATE users SET
                        first_name = %s, last_name = %s,
                        email = %s, avatar = %s
                    WHERE id = %s
                """
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    avatar_filename,
                    request.args['id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect(url_for('home'))
    return render_template('users_edit.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        password = request.form['password']
        encrypted_password = hashlib.sha256(password.encode()).hexdigest()
        # LOGIN
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = 'SELECT * FROM users WHERE email = %s AND password = %s'
                values = (
                    request.form['email'],
                    encrypted_password
                )
                cursor.execute(sql, values)
                result = cursor.fetchone()
        if result:
            session['logged_in'] = True
            session['first_name'] = result['first_name']
            session['email'] = result['email']
            session['role'] = result['role']
            session['id'] = result['id']
            return redirect(url_for('view_user', id=result['id']))
        else:
            return redirect('/login')
    else:
        return render_template('users_login.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    import os

    # This is required to allow flashing messages. We will cover this later.
    app.secret_key = os.urandom(32)

    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)
