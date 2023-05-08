from flask import Flask, jsonify, render_template, request
from pymysql import connections
import os
import traceback
import boto3
from config import *

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'employee'


@app.route("/", methods=['GET'])
def home():
    return render_template('index.html')

@app.route("/about", methods=['GET'])
def about():
    return render_template('about.html')

@app.route("/hire", methods=['GET'])
def hire():
    return render_template('hire.html')

@app.route("/info", methods=['GET'])
def info():
    return render_template('info.html')

@app.route("/update", methods=['GET'])
def update():
    return render_template('update.html')

@app.route("/fire", methods=['GET'])
def fire():
    return render_template('fire.html')

@app.route("/employees", methods=['GET'])
def employees():
    select_sql = "SELECT * FROM info"
    cursor = db_conn.cursor()
    cursor.execute(select_sql)
    results = cursor.fetchall()

    employees = []

    for result in results:
        employee = {
            'emp_id': result[0],
            'fname': result[1],
            'ic': result[2],
            'email': result[3],
            'location': result[4],
            'payscale': result[5]
        }
        employees.append(employee)

    cursor.close()

    return jsonify(employees)

@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    fname = request.form['fname']
    ic = request.form['ic']
    email = request.form['email']
    location = request.form['location']
    payscale = request.form['payscale']
    emp_image_file = request.files['emp_image_file']

    insert_sql = "INSERT INTO info VALUES (%s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        js = '''
            <script>
            alert("Please select a file!");
            </script>
            '''

    try:
        cursor.execute(insert_sql, (emp_id, fname, ic, email, location, payscale))
        db_conn.commit()
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)
            
            js = '''
            <script>
            alert("Employee added successfully!");
            </script>
            '''

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('hire.html')

@app.route("/searchEmp", methods=['POST'])
def searchEmp():
    emp_id = request.json['emp_id']

    select_sql = "SELECT * FROM info WHERE emp_id = %s"
    cursor = db_conn.cursor()

    try:
        try:
            cursor.execute(select_sql, (emp_id,))
            employee = cursor.fetchone()
        except Exception as e:
            print("Error retrieving image from S3:", str(e))

        if employee is None:
            print("Employee not found")
            return jsonify({'error': 'Employee not found'})

        # Extract the employee details from the database result
        emp_id = employee[0]
        fname = employee[1]
        ic = employee[2]
        email = employee[3]
        location = employee[4]
        payscale = employee[5]
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"

        # Retrieve the image from S3 bucket
        s3 = boto3.resource('s3')
        try:
            print("now trying s3 retrieve")
            response = s3.Object(custombucket, emp_image_file_name_in_s3)
            image_data = response.get()['Body'].read()

            # Save the image temporarily on the server
            temp_image_filename = "temp_image.jpg"
            temp_image_path = "employee/static/images/" + temp_image_filename  # Replace with the desired temporary image path

            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(temp_image_path), exist_ok=True)

            with open(temp_image_path, 'wb') as file:
                file.write(image_data)

            # Pass the temporary image path to the HTML input
            print("successfully retrieve image")
            return jsonify({
                'emp_id': emp_id,
                'fname': fname,
                'ic': ic,
                'email': email,
                'location': location,
                'payscale': payscale,
                'image_path': temp_image_path
            })

        except s3.meta.client.exceptions.NoSuchKey:
            print("Image file not found in S3 bucket.")
            return jsonify({'error': 'Image file not found'})

        except Exception as e:
            print("Error retrieving image from S3:", str(e))
            traceback.print_exc()
            return jsonify({'error': 'Error retrieving image from S3'})

    except Exception as e:
        return jsonify({'error': str(e)})

    finally:
        cursor.close()

@app.route("/updateEmp", methods=['POST'])
def updateEmp():
    data = request.form
    emp_id = data['emp_id']
    fname = data['fname']
    ic = data['ic']
    email = data['email']
    location = data['location']
    payscale = data['payscale']
    emp_image_file = request.files.get('emp_image_file')  # Get the uploaded image file

    # Update employee details in the database
    update_sql = "UPDATE info SET fname = %s, ic = %s, email = %s, location = %s, payscale = %s WHERE emp_id = %s"
    cursor = db_conn.cursor()
    try:
        cursor.execute(update_sql, (fname, ic, email, location, payscale, emp_id))
        db_conn.commit()

        if emp_image_file:
            # Uplaod image file in S3 #
            emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
            s3 = boto3.resource('s3')

            try:
                print("Data updated in MySQL RDS... uploading image to S3...")
                s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
                bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                s3_location = (bucket_location['LocationConstraint'])

                if s3_location is None:
                    s3_location = ''
                else:
                    s3_location = '-' + s3_location

                object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                    s3_location,
                    custombucket,
                    emp_image_file_name_in_s3)
                
                js = '''
                <script>
                alert("Employee data and image updated successfully!");
                </script>
                '''

            except Exception as e:
                return jsonify({'error': str(e)})

        else:
            js = '''
            <script>
            alert("Employee data updated successfully!");
            </script>
            '''

    except Exception as e:
        return jsonify({'error': str(e)})

    return jsonify({'status': 'success', 'message': js})


@app.route("/rmvemp", methods=['POST'])
def RmvEmp():
    emp_id = request.form['emp_id']

    select_sql = "SELECT * FROM info WHERE emp_id = %s"
    cursor = db_conn.cursor()
    cursor.execute(select_sql, (emp_id,))
    result = cursor.fetchone()

    emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
    s3 = boto3.resource('s3')

    if result is None:
        return "Employee not found"

    try:
        delete_sql = "DELETE FROM info WHERE emp_id=%s"
        cursor.execute(delete_sql, (emp_id,))
        db_conn.commit()
        emp_name = result[1]

        s3.Object(custombucket, emp_image_file_name_in_s3).delete()
    finally:
        cursor.close()

    print("Employee removed from database")
    return "Employee " + emp_name + " removed successfully"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

