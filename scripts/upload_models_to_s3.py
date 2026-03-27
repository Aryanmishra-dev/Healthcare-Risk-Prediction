import os
import boto3
import argparse

def main():
    parser = argparse.ArgumentParser(description="Upload local models to AWS S3")
    parser.add_argument("--bucket", required=True, help="Target S3 bucket name")
    args = parser.parse_args()
    
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MODEL_DIR = os.path.join(ROOT, "models")
    
    if not os.path.exists(MODEL_DIR):
        print(f"Error: Model directory {MODEL_DIR} not found.")
        return
    
    s3 = boto3.client('s3')
    
    uploaded_count = 0
    for filename in os.listdir(MODEL_DIR):
        if filename.endswith(".pkl") or filename.endswith(".json"):
            file_path = os.path.join(MODEL_DIR, filename)
            print(f"Uploading {filename} to s3://{args.bucket}/{filename}...")
            s3.upload_file(file_path, args.bucket, filename)
            uploaded_count += 1
            
    print(f"Success: {uploaded_count} models uploaded to {args.bucket}!")

if __name__ == "__main__":
    main()
