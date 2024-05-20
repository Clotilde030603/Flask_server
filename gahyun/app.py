from flask import Flask, render_template, session, request, url_for, redirect, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import hashlib
import sqlite3
import secrets
import os

app = Flask(__name__)
# 키값 설정
app.secret_key = secrets.token_hex(256)
# 세션 타임 설정
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=60)
# 세션 타입 설정
app.config['SESSION_TYPE'] = 'filesystem'

# 파일 타입 설정
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'hwp'}
# 프로젝트 루트 경로 설정
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
# 파일 업로드 경로 설정
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 업로드된 파일이 허용된 확장자인지 확인하는 함수를 정의합니다.
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 파일 업로드 경로가 존재하지 않으면 생성
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
    
def filename_sha_512_hash(data):
    # 데이터를 UTF-8 인코딩으로 변환하여 해싱합니다.
    encoded_data = data.encode('utf-8') + os.urandom(16)
    hashed_data = hashlib.sha512(encoded_data).hexdigest()
    return hashed_data

def password_sha_512_hash(data):
    # 데이터를 UTF-8 인코딩으로 변환하여 해싱합니다.
    encoded_data = data.encode('utf-8')
    hashed_data = hashlib.sha512(encoded_data).hexdigest()
    return hashed_data

# DB 연동
db_path = "main.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cur = conn.cursor() 

# 메인 페이지
@app.route('/')
def index():
    return render_template('index.html')

# 프로젝트 페이지
@app.route('/project')
def project():
    return render_template('project.html')

# 수상 페이지
@app.route('/awards')
def awards():
    return render_template('awards.html')

# 자유 게시판 글 쓰기 페이지
@app.route('/board_write', methods=['GET', 'POST'])
def board_write():
    if request.method == 'GET' :
        if 'username' not in session:
                error = "Login required"
                return redirect(url_for('error', error=error))
        return render_template('board_write.html')
    elif request.method == 'POST' :
        if 'username' not in session:
            error = "Login required"
            return redirect(url_for('error', error=error))
        try :
            title = request.form['title']
            contents = request.form['contents']
            u_id = session['id']
            username = session['username']
            status = 1

            # 파일 업로드 
            file = request.files['file']
            if file and allowed_file(file.filename):
                # 파일 크기 제한 설정 (최대 1MB)
                if len(file.read()) > 1024*1024*100:
                    msg = "파일 크기가 초과되었습니다. 최대 1MB까지 업로드 가능합니다."
                    return render_template('board_write.html', msg=msg)
                file.seek(0)  # 파일을 다시 읽을 수 있도록 커서 위치를 처음으로 이동시킴
                real_filename = file.filename
                hash_filename = filename_sha_512_hash(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], hash_filename))
            else:
                real_filename = None
                hash_filename = None

            insert_query = """
                INSERT INTO board (u_id, username, title, contents, status, real_filename, hash_filename) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
            cur.execute(insert_query, (u_id, username, title, contents, status, real_filename, hash_filename))
            conn.commit()
            return redirect(url_for('board_list'))
        except sqlite3.IntegrityError:
            msg = "게시글 작성 실패"
            return render_template('board_write.html', msg=msg)

# 자유 게시판 목록 페이지
@app.route('/board_list', methods=['GET'])
def board_list():
    try:
        if request.method == 'GET' :
            select_query = """
            SELECT id, username, title, mdate FROM board WHERE status = 1
            """
            cur.execute(select_query)
            posts = cur.fetchall()
            return render_template('board_list.html', posts=posts)
    except sqlite3.IntegrityError:
            error = "접근 불가"
            return render_template('error.html', error=error)

    
# 자유 게시판 글 보는 페이지
@app.route('/board_view', methods=['GET'])
def board_view():
    if 'username' not in session:
        error = "Login required"
        return redirect(url_for('error', error=error))
    id = request.args.get('id')
    status = 1
    select_query = """
    SELECT id, username, title, contents, real_filename FROM board WHERE id = ? and status = ?
    """
    cur.execute(select_query, (id, status))
    post = cur.fetchone() 
    return render_template('board_view.html', post=post)

# 다운로드 기능 
@app.route('/download/<category>/<id>/<real_filename>', methods=['GET'])
def download_file(category, id, real_filename):
    status = 1
    select_query = ""
    # board
    if category == 'board':
        select_query = """
        SELECT real_filename, hash_filename FROM board WHERE id = ? and real_filename = ? and status = ?
        """
    # qna
    elif category == 'qna':
        select_query = """
        SELECT real_filename, hash_filename FROM qna WHERE id = ? and real_filename = ? and status = ?
        """
    cur.execute(select_query, (id, real_filename, status))
    file = cur.fetchone()
    real_filename = file[0]
    hash_filename = file[1]
    print(real_filename)
    print(hash_filename)
    # 파일 경로 설정
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], hash_filename)
    # 파일이 존재하는지 확인하고 다운로드
    if os.path.exists(file_path):
        return send_file(file_path, download_name=real_filename, as_attachment=True)
    else:
        error='File not found'
        return redirect(url_for('error', error=error))
    
# 삭제
@app.route('/delete/<category>/<id>', methods=['GET'])
def delete(category, id):
    if 'username' not in session:
        error = "Login required"
        return redirect(url_for('error', error=error))
    status = 0
    update_query = ""
    username = session['username']
    # board
    if category == "board":
        update_query = """
        UPDATE board 
        SET status = ? 
        WHERE id = ? AND username = ? AND status = 1
        """
        cur.execute(update_query, (status, id, username))
        conn.commit()
        return redirect(url_for('board_list'))
    # qna
    elif category == "qna":
        update_query = """
        UPDATE qna 
        SET status = ? 
        WHERE id = ? AND username = ? AND status = 1
        """
        cur.execute(update_query, (status, id, username))
        conn.commit()
        return redirect(url_for('qna_list'))

# 수정
@app.route('/edit/<category>/<id>', methods=['GET', 'POST'])
def edit(category, id):
    username = session['username']
    if request.method == 'GET':
        if 'username' not in session:
            error = "Login required"
            return redirect(url_for('error', error=error))
        status = 1
        if category == 'board':
            select_query = """
            SELECT id, username, title, contents, real_filename FROM board WHERE id = ? and status = ? and username = ?
            """
            cur.execute(select_query, (id, status, username))
            post = cur.fetchone() 
            return render_template('board_edit.html', post=post)
        elif category == 'qna':
            select_query = """
            SELECT id, username, title, contents, real_filename FROM qna WHERE id = ? and status = ? and username = ?
            """
            cur.execute(select_query, (id, status, username))
            post = cur.fetchone() 
            return render_template('qna_edit.html', post=post)
    elif request.method == 'POST':
        if 'username' not in session:
            error = "Login required"
            return redirect(url_for('error', error=error))
        update_query = ""
        title = request.form['title']
        contents = request.form['contents']
        # board
        if category == 'board':
            update_query = """
            UPDATE board 
            SET title = ?, contents = ?
            WHERE id = ? AND username = ? AND status = 1
            """
            cur.execute(update_query, (title, contents, id, username))
            conn.commit()
            return redirect(url_for('board_list'))
        # qna
        elif category == 'qna':
            update_query = """
            UPDATE qna 
            SET title = ?, contents = ?
            WHERE id = ? AND username = ? AND status = 1
            """
            cur.execute(update_query, (title, contents, id, username))
            conn.commit()
            return redirect(url_for('qna_list'))
        


# qna 쓰기 페이지
@app.route('/qna_write', methods=['GET', 'POST'])
def qna_write():
    if request.method == 'GET' :
        if 'username' not in session:
            error = "Login required"
            return redirect(url_for('error', error=error))
        return render_template('qna_write.html')
    elif request.method == 'POST' :
        if 'username' not in session:
            error = "Login required"
            return redirect(url_for('error', error=error))
        try :
            title = request.form['title']
            contents = request.form['contents']
            u_id = session['id']
            username = session['username']
            status = 1

              # 파일 업로드 
            file = request.files['file']
            if file and allowed_file(file.filename):
                # 파일 크기 제한 설정 (최대 1MB)
                if len(file.read()) > 1024*1024*100:
                    msg = "파일 크기가 초과되었습니다. 최대 1MB까지 업로드 가능합니다."
                    return render_template('qna_write.html', msg=msg)
                file.seek(0)  # 파일을 다시 읽을 수 있도록 커서 위치를 처음으로 이동시킴
                real_filename = file.filename
                hash_filename = filename_sha_512_hash(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], hash_filename))
            else:
                real_filename = None
                hash_filename = None

            insert_query = """
                INSERT INTO qna (u_id, username, title, contents, status, real_filename, hash_filename) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
            cur.execute(insert_query, (u_id, username, title, contents, status, real_filename, hash_filename))
            conn.commit()
            return redirect(url_for('qna_list'))
        except sqlite3.IntegrityError:
            msg = "게시글 작성 실패"
            return render_template('qna_write.html', msg=msg)

# qna 목록 페이지
@app.route('/qna_list', methods=['GET'])
def qna_list():
    if request.method == 'GET' :
        select_query = """
        SELECT id, username, title, mdate FROM qna WHERE status = 1
        """
        cur.execute(select_query)
        posts = cur.fetchall()
        return render_template('qna_list.html', posts=posts)

# qna 글 보기 페이지
@app.route('/qna_view', methods=['GET'])
def qna_view():
    if 'username' not in session:
        error = "Login required"
        return redirect(url_for('error', error=error))
    id = request.args.get('id')
    status = 1
    select_query = """
    SELECT id, username, title, contents, real_filename FROM qna WHERE id = ? and status = ?
    """
    cur.execute(select_query, (id, status))
    post = cur.fetchone() 
    return render_template('qna_view.html', post=post)

# 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        try:
            id = request.form['id']
            password = request.form['password']
            password = password_sha_512_hash(password)
            select_query = """
            SELECT id, username, authority FROM user WHERE id = ? AND pw = ?
            """
            cur.execute(select_query, (id, password))
            user = cur.fetchone()
            select_query = """
            SELECT COUNT(*) FROM login_logs WHERE u_id = ? AND rdate > DATETIME('now', '-30 minute') 
            """
            cur.execute(select_query, (id, ))
            login_logs_count = cur.fetchone()
            if login_logs_count[0] >= 5 :
                msg = "5회 이상 틀렸습니다. 30분 뒤에 다시 시도 해주세요!"
                return render_template('login.html', msg=msg)
            if user is None:
                insert_query = """
                INSERT INTO login_logs (u_id) 
                VALUES (?)
                """
                cur.execute(insert_query, (id))
                conn.commit()
                return render_template('login.html')
            session['id'] = user[0]
            session['username'] = user[1]
            session['authority'] = user[2]
            return render_template('index.html')
        except sqlite3.IntegrityError:
            msg = "로그인 실패"
            return render_template('login.html', msg=msg)

# 회원가입
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    elif request.method == 'POST':
        try:
            id = request.form['id']
            name = request.form['name']
            username = request.form['username']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            email = request.form['email']
            phone_number = request.form['phone_number']
            authority = 0
            status = 1
            if password == confirm_password:
                password = password_sha_512_hash(password)
                insert_query = """
                INSERT INTO user (id, username, name, pw, email, phone, authority, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                cur.execute(insert_query, (id, username, name, password, email, phone_number, authority, status))
                conn.commit()
                return render_template('login.html')
        except sqlite3.IntegrityError:
            msg = "회원가입 실패"
            return render_template('signup.html', msg=msg)

# 로그아웃
@app.route('/logout', methods=['GET'])
def logout():
    if request.method == 'GET':
        session.clear()
        return render_template('index.html')

# 실행
if __name__ == '__main__':
    app.run('0.0.0.0', port=8000, debug=False)