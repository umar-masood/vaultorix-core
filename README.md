# Vaultorix - Server
This server is created using ```Python```. It will performs the following main operations:

1. Sends OTP to the client on its valid email-address.
2. Verify the OTP entered by the client in ```Vaultorix Application```.
3. Validates the user provided data in the form ```.json```.

Working - Sending an OTP: 
--------
```def send_otp(data: SendOTPModel, request: Request)``` <br>
<strong>1</strong>. When user enters his full name, username, and email-address in the application, then ```/sendOtp``` API endpoint will called and the specified data will sent to it in the following structure of ```json```

   <strong>Headers:</strong>
   ```
   "api_key" : API_KEY,
   "accept" : "application/json",
   "content-type" : "application/json"
   ```

   <strong>Required Data:</strong>
   ```
   {
     "name" : "name_of_the_client",
     "username" : "user_name",
     "email" : "email_of_client"
   }
   ```
   
<strong>2</strong>. Server takes user provided data from the request. <br>
<strong>3</strong>. Now evaluation process of request begins. <br>
   <strong>Step 1:</strong> First, the server will check the ```API KEY``` in the headers of the request. It will accepts the request if any of the following conditions is met:<br>
   &nbsp;&nbsp;&nbsp;<strong>a.</strong> ```API KEY``` must found in the ```headers``` of the request.<br>
   &nbsp;&nbsp;&nbsp;<strong>b.</strong> The provided ```API KEY``` must match with ```actual API KEY```.<br>
   If the request does not meet any of the above mentioned conditions then the server will return an error message to the client:
   ```
   "status_code": 400
   "message": "Something went wrong (API Key does not matched or its missing)."
   ```
   <strong>Step 2:</strong> In this step, the server will check the provided credentials ```(Email, Username and Full Name)``` to ensure they are valid:<br>
   ```def is_valid_name(name : str = '')``` <br>
   ```def is_valid_username(username: str = '')```<br>
   ```def is_valid_email(email: str = '')``` <br>
   In case if an email , username or full name is not valid then the server will return error message to the client:
   ```
   "status_code": 400
   "message": "Email, Username, or Full Name is missing in the given data."
   ```
   <strong>Step 3:</strong> In this step, ```Redis database connection``` is check to find out whether the connection is established properly or not?<br>
   ```def connect_to_redis()```<br>
   In case if it is not established then the server will return error message to the client:
   ```
   "status_code": 500
   "message": "Error connecting to the Redis Database."
   ```
   <strong>Step 4:</strong> Checking ```client IP Address``` and ```rate limiting``` data.<br>
   ```def get_client_real_ip(request: Request)```<br>
   ```def is_ip_blocked(ip: str)```<br>
   ```def check_existing_user(email: str)```<br>
   ```def is_max_attempts_reached(email: str)```<br>
   The request will not be acceptable if any of the following conditions is met:<br>
   &nbsp;&nbsp;&nbsp;<strong>a.</strong> If the user requested for OTP from ```same IP-Address``` more than ```3 times in 48 hours```.<br>
   &nbsp;&nbsp;&nbsp;<strong>b.</strong> If the user reached the maximum limit of ```resend OTP```.<br>
   If the request meet any of the above mentioned conditions then the server will return an error message to the client:
   ```
   "status_code": 429
   "message": "Too many requests from the same IP address, try again in 48hrs."
   ```
   <strong>Step 5:</strong> Then OTP will be generated and store in the Redis Database if the connection to it , is established properly otherwise the server will return an error response to the client:<br>
   ```def generate_otp()``` <br>
   ```def add_otp_to_redis_and_increment_counter(email: str, otp: str):``` <br>
   ```
   "status_code": 500
   "message": "An error occured (Error storing OTP data in the Redis Database)."
   ```
   <strong>Step 6:</strong> In this step, the ```OTP Email templete``` will prepare using the credentials of the client and then generated ```OTP``` will forwarded to that client<br>
   ```def email_data(html_content: str, receiver_name: str, receiver_email: str```<br>
   If there is any error in making ```template``` or ```send OTP to the client``` then server will return error responses respectively;
   ```
   "status_code": 500
   "message": "Error loading email template."
   ```
   ```
   "status_code": 502
   "message": "Email sending failed."
   ```
When all above steps are ```completed``` then finally server will return a message with status code:
```
   "status_code": 200
   "message": "OTP send successfully."
```
Working - Verifying an OTP: 
--------
```def verify_otp(data: VerifyOtpModel)```<br>
To verify the OTP, the client must provide the data in the following structure of ```.json``` when calling the ```/verifyOtp``` API endpoint.
```
{
"email" : "email_address",
"otp" : "user_provided_otp"
}
```
First, it will check the ```Redis connection```, then it will compare the ```user entered otp``` against the ```otp stored in the database```. If matched, then it will return the response to the client in the following structure:
```
{
   "isVerified" : True/False
}
