import requests

def test_login():
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    data = {"email": "test@example.com", "password": "Password123!"}
    
    # Try login
    res = requests.post("http://localhost:8000/auth/login", json=data, headers=headers)
    print("Login:", res.status_code, res.text)
    
    # Try register
    data["full_name"] = "Test User"
    res = requests.post("http://localhost:8000/auth/register", json=data, headers=headers)
    print("Register:", res.status_code, res.text)

if __name__ == "__main__":
    test_login()
