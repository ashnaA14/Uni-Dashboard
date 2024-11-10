from flask import Flask, render_template, redirect, send_file, url_for, request, flash,session,jsonify
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Cosmopolitan!22'
app.config['MYSQL_DB'] = 'uni_db'
app.config['MYSQL_HOST'] = 'localhost'
# app.config['UPLOAD_FOLDER'] = 'images'

mysql = MySQL(app)
bcrypt = Bcrypt(app)
# # create cursor execute, fetch close 

@app.route('/')
def login(): 
    return render_template('login.html')

# @app.route('/')
# def login():
#     print("Login route called")
#     return render_template('login.html')

@app.route('/pw' ,methods=['POST'])
def pw():
    currentpw=request.form['currentpw']
    newpw=request.form['newpw']
    confirmpw=request.form['confirmpw']
    #get users details
    if 'email' in session:
        email = session['email']
        cursor=mysql.connection.cursor()
        cursor.execute("SELECT * FROM signup where email=%s",(email,))
        user=cursor.fetchone()
        cursor.close() 
        #if current is actually current
        is_same = bcrypt.check_password_hash(user[3] , currentpw) #checks if pw in db is the same as currentpw entered
        if is_same:
            if(newpw==confirmpw): #if new n confirm blocks match
                hashed_password = bcrypt.generate_password_hash(newpw).decode('utf-8')
                is_valid = bcrypt.check_password_hash(hashed_password , currentpw) #checks if newpw and currentpw entered r the same
                if not is_valid :#new != old, update db
                    cursor = mysql.connection.cursor()
                    cursor.execute("UPDATE signup SET password=%s,confirm=%s WHERE email=%s",(hashed_password,hashed_password,email))
                    mysql.connection.commit()
                    cursor.close()
                    return render_template('password.html', message='New password has been set.')
                else:
                    return render_template('password.html', message='New password cannot be same as current password.')
            else:
                return render_template('password.html', message='Please make sure new and confirm passwords match.')
        else:
              return render_template('password.html', message='Wrong current password entered')


@app.route('/index')
def index():
    if 'email' in session:
        email = session['email']
        cursor=mysql.connection.cursor()
        cursor.execute("SELECT * FROM signup where email=%s",(email,))
        user=cursor.fetchone()
        print(user)
        cursor.execute("SELECT * FROM courses")
        courses=cursor.fetchall()
        cursor.execute("""SELECT COUNT(courses.courseid) AS num, courses.title FROM enrollments 
            INNER JOIN courses ON courses.courseid=enrollments.courseid
            GROUP BY courses.courseid""")
        tests=cursor.fetchall()
        cursor.execute("""SELECT timetable.*, courses.title FROM timetable 
                       INNER JOIN courses ON timetable.course_id=courses.courseid
                       ORDER BY timetable.day, timetable.start_time""")
        timetable=cursor.fetchall()
        # PASS STUDENT ID TO enrollment table get ti course id use it to reference courses table and grab data 
        cursor.execute("""SELECT timetable.*,courses.title FROM enrollments
                       INNER JOIN timetable ON enrollments.courseid=timetable.course_id
                       INNER JOIN courses ON enrollments.courseid=courses.courseid
                       WHERE enrollments.studentid=%s""",(user[0],))
        subs=cursor.fetchall()
        print("subject list per student: ",subs)
        cursor.execute("""SELECT attendance.date,attendance.approval_status, courses.title 
                       from attendance INNER JOIN courses ON attendance.course_id=courses.courseid WHERE student_id=%s""",(user[0],))
        data=cursor.fetchall()
        cursor.close()
        print(user[7])     
        return render_template('index.html',user=user,name=user[1],email=email,dob=user[5],number=user[6],role=user[7],courses=courses,tests=tests,timetable=timetable,subs=subs,data=data)

@app.route('/logout')
def logout():
    session.clear()
    return render_template('login.html')

@app.route('/add')
def add():
    return render_template('add.html')


@app.route('/attendance')
def attendance():
    if 'email' in session:
        email = session['email']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT role FROM signup WHERE email=%s", (email,))
        role = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM signup WHERE email=%s", (email,))
        student_id = cursor.fetchone()[0]
        cursor.execute("""
            SELECT courses.courseid, courses.title
            FROM enrollments
            INNER JOIN courses ON enrollments.courseid = courses.courseid
            WHERE enrollments.studentid = %s
        """, (student_id,))
        enrolled_courses = cursor.fetchall()
        cursor.execute("""
            SELECT attendance.*, courses.title, signup.name
            FROM attendance
            INNER JOIN courses ON attendance.course_id = courses.courseid
            INNER JOIN signup ON attendance.student_id = signup.id
            WHERE approval_status = 'pending'
        """)
        pending = cursor.fetchall()
        print("pending: ",pending)

        cursor.execute("""
            SELECT attendance.date, attendance.approval_status, courses.title
            FROM attendance
            INNER JOIN courses ON attendance.course_id = courses.courseid
        """)
        data = cursor.fetchall()
        cursor.close()
        return render_template('attendance.html', role=role, enrolled_courses=enrolled_courses, data=data, student_id=student_id, pending=pending)



@app.route('/students')
def students(): #if admins email is in session, go to db and collect only students to pass to student table
    cursor=mysql.connection.cursor()
    cursor.execute("SELECT * FROM signup WHERE role= 2")
    users=cursor.fetchall()
    cursor.close()
    return render_template('students.html',users=users)

@app.route('/password')
def password():
    if 'email' in session:
        email = session['email']
        cursor=mysql.connection.cursor()
        cursor.execute("SELECT role from signup WHERE email=%s",(email,))
        role=cursor.fetchone()
        cursor.close()
        return render_template('password.html',role=role[0])


@app.route('/mark', methods=['POST'])
def mark_attendance():
    student_id = request.form.get('student_id')
    course_id = request.form.get('course_id')
    date = request.form.get('date')
    status = request.form.get('status')
    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO attendance (student_id, course_id, date, status)
        VALUES (%s, %s, %s, %s)
    """, (student_id, course_id, date, status))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('index'))  
    

@app.route('/attendance/approve', methods=['POST'])
def approve_attendance():
    if 'email' in session:
        email = session['email']
        attendance_id = request.form.get('attendance_id')
        attendance_date=request.form.get('attendance_date')
        cursor=mysql.connection.cursor()
        cursor.execute("""UPDATE attendance SET approval_status='approved' WHERE attendance_id=%s""",(attendance_id,)) #use attendance id instead
        mysql.connection.commit()
        cursor.close()
        print(f"Updated attendance with ID: {attendance_id} on Date: {attendance_date}")
        return redirect(url_for('attendance'))

@app.route('/attendance/deny', methods=['POST'])
def deny_attendance():
    if 'email' in session:
        email = session['email']
        attendance_id = request.form.get('attendance_id')
        cursor=mysql.connection.cursor()
        cursor.execute("""UPDATE attendance SET approval_status='rejected' WHERE attendance_id=%s""",(attendance_id,)) #use attendance id instead
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('attendance'))



@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    email = request.form.get('email')
    dob = request.form.get('dob')
    number= request.form.get('number')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm')
    

    cursor=mysql.connection.cursor()
    cursor.execute("SELECT * FROM signup WHERE email=%s",(email,))
    user=cursor.fetchone()
    
    cursor.close()
    if user:
        return render_template('login.html', message='user already exists. please sign in.')

    elif(password!=confirm_password):
        return render_template('login.html', message='password and comfirmed password dont match. try agai')

    else:
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor=mysql.connection.cursor()
        cursor.execute("INSERT INTO signup(name,email,password,confirm,dob,contact) VALUES (%s ,%s ,%s,%s,%s,%s)",(name,email,hashed_password,hashed_password,dob,number))
        mysql.connection.commit()
        cursor.close()
    return redirect('/')  

@app.route('/signin' , methods=['POST'])
def signin():
    email=request.form['email']
    password=request.form['password']
    cursor=mysql.connection.cursor()
    cursor.execute("SELECT * FROM signup where email=%s",(email,))
    user=cursor.fetchone()
    cursor.close()
    if user: 
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT role.type
            FROM signup
            INNER JOIN role ON signup.role=role.role_id
            WHERE signup.email=%s
                    """,(email,))
        role = cursor.fetchone()
        cursor.execute("SELECT name FROM signup where email=%s",(email,))
        usrname=cursor.fetchone()
        cursor.execute("SELECT * FROM courses")
        courses=cursor.fetchall()
        cursor.execute("""SELECT COUNT(courses.courseid) AS num, courses.title FROM enrollments 
            INNER JOIN courses ON courses.courseid=enrollments.courseid
            GROUP BY courses.courseid""")
        tests=cursor.fetchall()
        cursor.execute("""SELECT timetable.*, courses.title FROM timetable 
                       INNER JOIN courses ON timetable.course_id=courses.courseid
                       ORDER BY timetable.day, timetable.start_time""")
        timetable=cursor.fetchall()
        print("timetable: ",timetable)
        cursor.execute("""SELECT timetable.*,courses.title FROM enrollments
                       INNER JOIN timetable ON enrollments.courseid=timetable.course_id
                       INNER JOIN courses ON enrollments.courseid=courses.courseid
                       WHERE enrollments.studentid=%s""",(user[0],))
        subs=cursor.fetchall()
        cursor.execute("""SELECT attendance.date,attendance.approval_status, courses.title 
                       from attendance INNER JOIN courses ON attendance.course_id=courses.courseid 
                       WHERE student_id=%s""",(user[0],))
        data=cursor.fetchall()
        print("data: ",data)
        
        cursor.close()
        hashpw=user[3]
        is_valid = bcrypt.check_password_hash(hashpw, password)  
        if is_valid:
            session['email'] = email
            return render_template('index.html',name=usrname[0],email=email,dob=user[5],number=user[6],role=role[0],courses=courses,tests=tests,timetable=timetable,subs=subs,data=data)
        else:
            return render_template('login.html', message='Wrong password. Please try again.')
    else:
        return render_template('login.html', message='User doesnt exist. please sign up!')

@app.route('/courses/<int:id>')
def courses(id):
    print("id: ",id)
    cursor=mysql.connection.cursor()
    cursor.execute("""SELECT title,description,instructor FROM courses
                   INNER JOIN enrollments ON courses.courseid=enrollments.courseid
                   INNER JOIN signup ON enrollments.studentid=signup.id
                    WHERE ID=%s""",(id,))
    courses=cursor.fetchall()
    cursor.close()
    print(courses) #returned (('dsa',), ('stats',))
    return render_template('courses.html',courses=courses)

@app.route('/class/<int:class_id>')
def class_details(class_id):
    print("id: ",class_id)
    # Fetch and display class details using class_id
    #pass class id. fetch from db only details of class id match 
    cursor=mysql.connection.cursor()
    cursor.execute("""
    SELECT timetable.*, courses.title 
    FROM timetable 
    INNER JOIN courses ON timetable.course_id = courses.courseid
    WHERE timetable.course_id = %s
    ORDER BY timetable.day, timetable.start_time
    """, (class_id,))
    details=cursor.fetchall()
    cursor.close()
    print(details)
    return render_template('class_details.html', class_id=class_id,details=details)
 

if __name__=='__main__':
    app.run(debug=True)


